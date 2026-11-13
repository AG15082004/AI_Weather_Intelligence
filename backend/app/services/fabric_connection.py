"""Microsoft Fabric SQL connection service.

Manages connectivity to Microsoft Fabric SQL Analytics Endpoints using pyodbc
with ODBC Driver 18 and Microsoft Entra ID authentication.
Supports:
  - azure_cli (local development via AzureCliCredential and SQL_COPT_SS_ACCESS_TOKEN)
  - interactive (ActiveDirectoryInteractive via browser/WAM)
  - service_principal (ActiveDirectoryServicePrincipal with client ID & secret)
"""

import asyncio
import os
import struct
import time
from typing import Any, Dict, Optional, Tuple

import pyodbc
import structlog
from azure.identity import AzureCliCredential

from app.config import Settings, get_settings

log = structlog.get_logger()

# ODBC SQL_COPT_SS_ACCESS_TOKEN attribute constant
SQL_COPT_SS_ACCESS_TOKEN = 1256
AZURE_SQL_RESOURCE = "https://database.windows.net/.default"


class FabricConnectionError(Exception):
    """Fabric SQL connection failure or service unavailable."""
    pass


def is_transient_connection_error(exc: Exception) -> bool:
    """Identify transient network or temporary login glitches eligible for retry."""
    err_str = str(exc).lower()
    transient_indicators = [
        "login timeout",
        "hyt00",
        "08s01",
        "08001",
        "10054",
        "10060",
        "communication link failure",
        "connection reset",
        "token expired",
        "fa004",
        "28000",
    ]
    return any(ind in err_str for ind in transient_indicators)


class FabricConnectionService:
    """Manages connections to Microsoft Fabric Lakehouse SQL endpoints.

    Provides secure token-based connection via Azure CLI, interactive Entra ID,
    and Service Principal authentication, with token expiration caching.
    """

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self._settings = settings or get_settings()
        self._connection: Optional[pyodbc.Connection] = None

        # Token caching state: (packed_token_bytes, expires_on_epoch)
        self._cached_token_struct: Optional[bytes] = None
        self._cached_token_expires_on: float = 0.0

    @property
    def auth_mode(self) -> str:
        """Effective authentication mode ('azure_cli', 'service_principal', or 'deferred')."""
        mode, _ = self.resolve_auth_mode()
        return mode

    def is_driver_available(self) -> bool:
        """Check if configured ODBC driver is registered on the host system."""
        try:
            drivers = pyodbc.drivers()
            target = (self._settings.fabric_odbc_driver or "").strip().lower()
            return any(d.strip().lower() == target for d in drivers)
        except Exception as exc:
            log.warning("odbc_driver_check_failed", error=str(exc))
            return False

    def resolve_auth_mode(self) -> Tuple[str, str]:
        """Resolve effective authentication mode and diagnostic reason.

        Returns:
            (mode, reason)
            mode: 'azure_cli', 'service_principal', or 'deferred'
        """
        server = (self._settings.fabric_server or "").strip()
        if not server:
            return "deferred", "fabric_server_unconfigured"

        if not self.is_driver_available():
            driver_name = self._settings.fabric_odbc_driver
            return "deferred", f"odbc_driver_missing: '{driver_name}' not found on host"

        is_cloud_prod = (
            (self._settings.app_env or "development").strip().lower() in ("production", "staging")
            or bool(os.environ.get("RENDER"))
        )

        has_spn = bool(
            self._settings.fabric_client_id
            and self._settings.fabric_client_secret
            and len(self._settings.fabric_client_id.strip()) > 5
            and len(self._settings.fabric_client_secret.strip()) > 5
        )

        if is_cloud_prod:
            if has_spn:
                return "service_principal", "production_service_principal_ready"
            # Never attempt interactive browser/WAM or local Azure CLI on cloud host
            return "deferred", "production_service_principal_credentials_deferred"

        # Local development
        raw_mode = (self._settings.fabric_auth_mode or "azure_cli").strip().lower()
        if raw_mode in ("service_principal", "spn") and has_spn:
            return "service_principal", "development_service_principal_ready"

        return "azure_cli", "development_azure_cli_ready"

    def validate_configuration(self) -> Dict[str, Any]:
        """Validate Fabric configuration at startup without exposing secrets.

        Returns safe diagnostic metadata.
        """
        mode, reason = self.resolve_auth_mode()
        driver_ok = self.is_driver_available()
        summary = self.get_safe_summary()
        status = "ready" if mode in ("azure_cli", "service_principal") else "deferred"

        log.info(
            "fabric_startup_configuration_validated",
            status=status,
            effective_auth_mode=mode,
            reason=reason,
            driver=self._settings.fabric_odbc_driver,
            driver_available=driver_ok,
            database=self._settings.fabric_database,
            server_configured=bool(self._settings.fabric_server),
        )
        return {
            "status": status,
            "effective_auth_mode": mode,
            "reason": reason,
            "driver_available": driver_ok,
            "summary": summary,
        }

    def get_token_struct(self) -> bytes:
        """Acquire SQL access token via Azure CLI and pack for ODBC attribute 1256.

        Refreshes token automatically if expired or within 300 seconds of expiry.
        Token strings are never logged or exposed.
        """
        now = time.time()
        # Reuse cached token if valid for at least 5 more minutes
        if self._cached_token_struct and now < (self._cached_token_expires_on - 300):
            return self._cached_token_struct

        log.info("acquiring_azure_cli_token", resource=AZURE_SQL_RESOURCE)
        credential = AzureCliCredential()
        token_obj = credential.get_token(AZURE_SQL_RESOURCE)

        access_token = token_obj.token
        expires_on = float(token_obj.expires_on)

        # Convert token to UTF-16-LE bytes and pack with unsigned 32-bit little-endian length prefix
        token_bytes = access_token.encode("utf-16-le")
        token_struct = struct.pack(
            f"<I{len(token_bytes)}s",
            len(token_bytes),
            token_bytes,
        )

        self._cached_token_struct = token_struct
        self._cached_token_expires_on = expires_on

        log.info(
            "azure_cli_token_acquired",
            expires_in_seconds=int(expires_on - now),
        )
        return token_struct

    def get_service_principal_token_struct(self) -> bytes:
        """Acquire SQL access token via Entra Service Principal and pack for ODBC attribute 1256.

        Refreshes token automatically if expired or within 300 seconds of expiry.
        Token strings are never logged or exposed.
        """
        now = time.time()
        if self._cached_token_struct and now < (self._cached_token_expires_on - 300):
            return self._cached_token_struct

        log.info(
            "acquiring_service_principal_token",
            resource=AZURE_SQL_RESOURCE,
            has_tenant=bool(self._settings.fabric_tenant_id),
            has_client=bool(self._settings.fabric_client_id),
        )

        from azure.identity import ClientSecretCredential

        credential = ClientSecretCredential(
            tenant_id=self._settings.fabric_tenant_id,
            client_id=self._settings.fabric_client_id,
            client_secret=self._settings.fabric_client_secret,
        )
        token_obj = credential.get_token(AZURE_SQL_RESOURCE)
        access_token = token_obj.token
        expires_on = float(token_obj.expires_on)

        token_bytes = access_token.encode("utf-16-le")
        token_struct = struct.pack(
            f"<I{len(token_bytes)}s",
            len(token_bytes),
            token_bytes,
        )

        self._cached_token_struct = token_struct
        self._cached_token_expires_on = expires_on

        log.info(
            "service_principal_token_acquired",
            expires_in_seconds=int(expires_on - now),
        )
        return token_struct

    def build_connection_params(self) -> Tuple[str, Optional[Dict[int, bytes]]]:
        """Build ODBC connection string and optional attrs_before dictionary.

        Returns:
            Tuple of (connection_string, attrs_before_dict)
        """
        driver = self._settings.fabric_odbc_driver
        server = self._settings.fabric_server
        database = self._settings.fabric_database
        encrypt = self._settings.fabric_encrypt
        trust_cert = self._settings.fabric_trust_server_certificate
        mode = self.auth_mode

        if mode == "azure_cli":
            # For token-based auth, DO NOT include UID, PWD, or Authentication
            conn_str = (
                f"Driver={{{driver}}};"
                f"Server={server};"
                f"Database={database};"
                f"Encrypt={encrypt};"
                f"TrustServerCertificate={trust_cert};"
                "APP=TN_Weather_Intelligence_Platform;"
            )
            token_struct = self.get_token_struct()
            return conn_str, {SQL_COPT_SS_ACCESS_TOKEN: token_struct}

        elif mode == "service_principal":
            parts = [
                f"Driver={{{driver}}}",
                f"Server={server}",
                f"Database={database}",
                "Authentication=ActiveDirectoryServicePrincipal",
                f"Encrypt={encrypt}",
                f"TrustServerCertificate={trust_cert}",
                f"LoginTimeout={self._settings.fabric_connection_timeout}",
                "APP=TN_Weather_Intelligence_Platform",
            ]
            if self._settings.fabric_client_id:
                parts.append(f"UID={self._settings.fabric_client_id}")
            if self._settings.fabric_client_secret:
                parts.append(f"PWD={self._settings.fabric_client_secret}")
            return ";".join(parts) + ";", None

        else:
            # ActiveDirectoryInteractive
            parts = [
                f"Driver={{{driver}}}",
                f"Server={server}",
                f"Database={database}",
                "Authentication=ActiveDirectoryInteractive",
                f"Encrypt={encrypt}",
                f"TrustServerCertificate={trust_cert}",
                f"LoginTimeout={self._settings.fabric_connection_timeout}",
                "APP=TN_Weather_Intelligence_Platform",
            ]
            if self._settings.fabric_username:
                parts.append(f"UID={self._settings.fabric_username}")
            return ";".join(parts) + ";", None

    @property
    def connection_string(self) -> str:
        """Return base connection string without token data."""
        conn_str, _ = self.build_connection_params()
        return conn_str

    def get_safe_summary(self) -> Dict[str, Any]:
        """Return a sanitized summary of connection configuration without secrets."""
        server = self._settings.fabric_server or "not_configured"
        masked_server = server
        if len(server) > 30 and "." in server:
            prefix = server[:12]
            suffix = server[server.find(".") :]
            masked_server = f"{prefix}...{suffix}"

        token_cached = bool(
            self._cached_token_struct
            and time.time() < (self._cached_token_expires_on - 60)
        )
        mode, reason = self.resolve_auth_mode()

        return {
            "server": masked_server,
            "database": self._settings.fabric_database,
            "configured_auth_mode": (self._settings.fabric_auth_mode or "azure_cli"),
            "effective_auth_mode": mode,
            "auth_status_reason": reason,
            "driver": self._settings.fabric_odbc_driver,
            "driver_available": self.is_driver_available(),
            "encrypt": self._settings.fabric_encrypt,
            "trust_server_certificate": self._settings.fabric_trust_server_certificate,
            "timeout_seconds": self._settings.fabric_connection_timeout,
            "token_cached": token_cached,
            "has_tenant_id": bool(self._settings.fabric_tenant_id),
            "has_client_id": bool(self._settings.fabric_client_id),
            "has_username": bool(self._settings.fabric_username),
        }

    async def connect(self) -> pyodbc.Connection:
        """Establish or return an active pyodbc connection.

        Returns:
            Active pyodbc.Connection.
        """
        mode, reason = self.resolve_auth_mode()
        if mode == "deferred":
            log.warning("fabric_connection_deferred", reason=reason)
            raise FabricConnectionError(f"Microsoft Fabric connectivity is DEFERRED ({reason})")

        if self._connection is not None:
            try:
                cur = self._connection.cursor()
                cur.execute("SELECT 1")
                cur.close()
                return self._connection
            except Exception:
                log.warning("fabric_cached_connection_dead_reconnecting")
                self._connection = None

        log.info(
            "fabric_connecting",
            server=self._settings.fabric_server[:15] + "..." if self._settings.fabric_server else "",
            database=self._settings.fabric_database,
            auth_mode=mode,
        )

        max_retries = max(0, getattr(self._settings, "fabric_max_retries", 2))
        last_exception: Optional[Exception] = None

        for attempt in range(1, max_retries + 2):
            conn_str, attrs = self.build_connection_params()
            try:
                if attrs:
                    self._connection = pyodbc.connect(
                        conn_str,
                        attrs_before=attrs,
                        timeout=self._settings.fabric_connection_timeout,
                    )
                else:
                    self._connection = pyodbc.connect(
                        conn_str,
                        timeout=self._settings.fabric_connection_timeout,
                    )
                log.info("fabric_connected_successfully", attempt=attempt)
                return self._connection
            except Exception as exc:
                last_exception = exc
                log.warning(
                    "fabric_connection_attempt_failed",
                    attempt=attempt,
                    max_attempts=max_retries + 1,
                    error_type=type(exc).__name__,
                )
                # Invalidate cached token in case failure is authentication/token expiry
                self._cached_token_struct = None
                self._cached_token_expires_on = 0.0

                if attempt <= max_retries and is_transient_connection_error(exc):
                    backoff = 0.5 * (2 ** (attempt - 1))
                    log.info("retrying_fabric_connection", backoff_seconds=backoff)
                    await asyncio.sleep(backoff)
                else:
                    break

        log.error("fabric_connection_failed", error=str(last_exception))
        if last_exception:
            raise last_exception
        raise RuntimeError("Failed to establish Microsoft Fabric connection")

    async def disconnect(self) -> None:
        """Close the active connection cleanly."""
        if self._connection is not None:
            try:
                self._connection.close()
                log.info("fabric_connection_closed")
            except Exception as exc:
                log.warning("fabric_disconnect_error", error=str(exc))
            finally:
                self._connection = None

    async def verify_connection(self) -> Dict[str, Any]:
        """Verify Fabric SQL connection by executing SELECT 1 AS connection_status.

        Returns:
            Dict containing connection status, latency, diagnostic info,
            and error analysis if failed. Never exposes secrets or tokens.
        """
        start_time = time.perf_counter()
        summary = self.get_safe_summary()
        mode, reason = self.resolve_auth_mode()

        if mode == "deferred":
            try:
                from app.services.data_reliability_service import data_reliability_service
                from app.services.metrics_service import metrics_service
                metrics_service.record_fabric_check(False)
                data_reliability_service.record_connectivity_check(False)
            except Exception:
                pass
            return {
                "status": "deferred",
                "connected": False,
                "reason": reason,
                "driver_available": self.is_driver_available(),
                "details": summary,
                "suggestion": "Configure FABRIC_SERVER and Service Principal credentials (or install msodbcsql18 via Docker) to enable cloud Fabric connectivity.",
            }

        try:
            conn = await self.connect()
            cursor = conn.cursor()
            cursor.execute("SELECT 1 AS connection_status")
            row = cursor.fetchone()
            cursor.close()

            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            result_val = row[0] if row else None

            if result_val == 1:
                try:
                    from app.services.data_reliability_service import data_reliability_service
                    from app.services.metrics_service import metrics_service
                    metrics_service.record_fabric_query(success=True, duration_ms=latency_ms)
                    metrics_service.record_fabric_check(True)
                    data_reliability_service.record_connectivity_check(True)
                except Exception:
                    pass
                return {
                    "status": "connected",
                    "connected": True,
                    "query_status": 1,
                    "latency_ms": latency_ms,
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "details": summary,
                }
            else:
                try:
                    from app.services.data_reliability_service import data_reliability_service
                    from app.services.metrics_service import metrics_service
                    metrics_service.record_fabric_query(success=False, duration_ms=latency_ms)
                    metrics_service.record_fabric_check(False)
                    data_reliability_service.record_connectivity_check(False)
                except Exception:
                    pass
                return {
                    "status": "error",
                    "connected": False,
                    "error": f"Unexpected verification response: {result_val}",
                    "latency_ms": latency_ms,
                    "details": summary,
                }

        except pyodbc.Error as odbc_err:
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            raw_msg = str(odbc_err)
            diag_hint = self._diagnose_odbc_error(raw_msg)
            try:
                from app.services.data_reliability_service import data_reliability_service
                from app.services.metrics_service import metrics_service
                metrics_service.record_fabric_query(success=False, duration_ms=latency_ms)
                metrics_service.record_fabric_check(False)
                data_reliability_service.record_connectivity_check(False)
            except Exception:
                pass

            return {
                "status": "error",
                "connected": False,
                "error_type": type(odbc_err).__name__,
                "error": self._clean_error_message(raw_msg),
                "latency_ms": latency_ms,
                "details": summary,
                "diagnosis": diag_hint,
            }
        except Exception as exc:
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            try:
                from app.services.data_reliability_service import data_reliability_service
                from app.services.metrics_service import metrics_service
                metrics_service.record_fabric_query(success=False, duration_ms=latency_ms)
                metrics_service.record_fabric_check(False)
                data_reliability_service.record_connectivity_check(False)
            except Exception:
                pass
            return {
                "status": "error",
                "connected": False,
                "error_type": type(exc).__name__,
                "error": str(exc),
                "latency_ms": latency_ms,
                "details": summary,
            }

    def _clean_error_message(self, msg: str) -> str:
        """Sanitize error messages to avoid accidental password or token leakage."""
        clean = msg
        for kw in ["PWD=", "Password=", "client_secret="]:
            if kw in clean:
                parts = clean.split(kw)
                clean = parts[0] + kw + "***"
        return clean.strip()

    def _diagnose_odbc_error(self, err_text: str) -> str:
        """Provide helpful diagnostic advice based on ODBC Driver error patterns."""
        lower = err_text.lower()
        if "token" in lower or "copt_ss_access_token" in lower:
            return "Azure CLI token error or expiration. Try running 'az login' again."
        if "login failed" in lower:
            return (
                "Login failed for the provided identity. Please ensure the user or Service Principal "
                "has 'ReadData' permissions on the Lakehouse 'lh_tn_weather_intelligence' in the Fabric workspace."
            )
        if "cannot open database" in lower or "database" in lower and "does not exist" in lower:
            return f"Database '{self._settings.fabric_database}' was not found on this SQL endpoint. Verify Lakehouse name."
        if "timeout" in lower or "08001" in lower:
            return "Connection timed out connecting to the SQL endpoint. Check network connectivity, firewall, and server address."
        return "Check Microsoft Fabric SQL Endpoint configuration, network access, and Entra ID permissions."
