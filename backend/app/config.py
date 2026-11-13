"""Application configuration using Pydantic BaseSettings.

Loads settings from environment variables and .env file.
"""

"""Application configuration using Pydantic BaseSettings.

Loads settings from environment variables and .env file.
"""

from typing import Any, List, Optional
from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Environment
    app_env: str = Field(
        default="development",
        validation_alias=AliasChoices("APP_ENV", "ENVIRONMENT"),
        description="Application environment (development, staging, production)",
    )

    # Microsoft Fabric SQL Connection
    fabric_server: str = Field(
        default="",
        validation_alias=AliasChoices("FABRIC_SERVER", "FABRIC_SQL_ENDPOINT", "AZURE_SQL_SERVER"),
        description="Microsoft Fabric SQL endpoint / server URL",
    )
    fabric_database: str = Field(
        default="lh_tn_weather_intelligence",
        validation_alias=AliasChoices("FABRIC_DATABASE", "AZURE_SQL_DATABASE"),
        description="Fabric database / Lakehouse name",
    )
    fabric_auth_mode: str = Field(
        default="azure_cli",
        validation_alias=AliasChoices("FABRIC_AUTH_MODE", "FABRIC_AUTHENTICATION"),
        description="Fabric authentication method (azure_cli, service_principal, interactive)",
    )
    fabric_tenant_id: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("FABRIC_TENANT_ID", "AZURE_TENANT_ID"),
        description="Entra ID Tenant ID for Fabric connection",
    )
    fabric_username: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("FABRIC_USERNAME", "FABRIC_USER", "FABRIC_UID"),
        description="Optional Entra ID username/UPN for interactive or password login",
    )
    fabric_password: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("FABRIC_PASSWORD", "FABRIC_PWD"),
        description="Optional password for password authentication",
    )
    fabric_client_id: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("FABRIC_CLIENT_ID", "AZURE_CLIENT_ID"),
        description="Service Principal Client ID (future production auth)",
    )
    fabric_client_secret: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("FABRIC_CLIENT_SECRET", "AZURE_CLIENT_SECRET"),
        description="Service Principal Client Secret (future production auth)",
    )
    fabric_odbc_driver: str = Field(
        default="ODBC Driver 18 for SQL Server",
        validation_alias=AliasChoices("FABRIC_ODBC_DRIVER"),
        description="ODBC driver name installed on host",
    )
    fabric_encrypt: str = Field(
        default="yes",
        validation_alias=AliasChoices("FABRIC_ENCRYPT"),
        description="Encrypt connection (yes/no)",
    )
    fabric_trust_server_certificate: str = Field(
        default="yes",
        validation_alias=AliasChoices("FABRIC_TRUST_SERVER_CERTIFICATE", "FABRIC_TRUST_SERVER_CERT"),
        description="Trust server certificate (yes/no)",
    )
    fabric_connection_timeout: int = Field(
        default=30,
        validation_alias=AliasChoices("FABRIC_CONNECTION_TIMEOUT", "FABRIC_CONNECT_TIMEOUT"),
        description="Fabric connection timeout in seconds",
    )
    fabric_query_timeout: int = Field(
        default=25,
        validation_alias=AliasChoices("FABRIC_QUERY_TIMEOUT"),
        description="Fabric SQL query execution timeout in seconds",
    )
    fabric_max_retries: int = Field(
        default=2,
        validation_alias=AliasChoices("FABRIC_MAX_RETRIES"),
        description="Max connection retries for transient failures",
    )

    @field_validator("app_env", mode="before")
    @classmethod
    def _clean_app_env(cls, v: Any) -> str:
        if isinstance(v, str) and v.strip():
            return v.strip().lower()
        return "development"

    @field_validator("fabric_server", mode="before")
    @classmethod
    def _clean_fabric_server(cls, v: Any) -> str:
        if isinstance(v, str):
            return v.strip()
        return ""

    @field_validator("fabric_database", mode="before")
    @classmethod
    def _clean_fabric_database(cls, v: Any) -> str:
        if isinstance(v, str) and v.strip():
            return v.strip()
        return "lh_tn_weather_intelligence"

    @field_validator("fabric_auth_mode", mode="before")
    @classmethod
    def _clean_fabric_auth_mode(cls, v: Any) -> str:
        if isinstance(v, str) and v.strip():
            return v.strip().lower()
        return "azure_cli"

    @field_validator("fabric_odbc_driver", mode="before")
    @classmethod
    def _clean_fabric_odbc_driver(cls, v: Any) -> str:
        if isinstance(v, str) and v.strip():
            return v.strip()
        return "ODBC Driver 18 for SQL Server"

    @field_validator("fabric_trust_server_certificate", mode="before")
    @classmethod
    def _clean_fabric_trust_cert(cls, v: Any) -> str:
        if isinstance(v, str) and v.strip():
            return v.strip().lower()
        return "yes"

    @field_validator(
        "fabric_tenant_id",
        "fabric_username",
        "fabric_password",
        "fabric_client_id",
        "fabric_client_secret",
        mode="before",
    )
    @classmethod
    def _clean_optional_string(cls, v: Any) -> Optional[str]:
        if isinstance(v, str):
            cleaned = v.strip()
            return cleaned if cleaned else None
        return v

    # Compatibility properties for existing code
    @property
    def fabric_sql_endpoint(self) -> str:
        return self.fabric_server

    @property
    def fabric_authentication(self) -> str:
        return self.fabric_auth_mode

    # Ollama & AI Configuration
    ai_provider: str = Field(
        default="auto",
        validation_alias=AliasChoices("AI_PROVIDER"),
        description="AI provider strategy: auto, openai, ollama, or deterministic",
    )
    openai_api_key: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("OPENAI_API_KEY"),
        description="OpenAI API Key for GPT-6 Luna online responses",
    )
    openai_model: str = Field(
        default="gpt-6-luna",
        validation_alias=AliasChoices("OPENAI_MODEL"),
        description="OpenAI model name to use for online AI features",
    )
    openai_timeout_seconds: float = Field(
        default=30.0,
        validation_alias=AliasChoices("OPENAI_TIMEOUT_SECONDS", "OPENAI_TIMEOUT"),
        description="Timeout for OpenAI Responses API requests in seconds",
    )
    openai_max_output_tokens: int = Field(
        default=1024,
        validation_alias=AliasChoices("OPENAI_MAX_OUTPUT_TOKENS"),
        description="Maximum output tokens for OpenAI generation",
    )
    ollama_base_url: str = Field(
        default="http://127.0.0.1:11434",
        description="Ollama API base URL",
    )
    ollama_model: str = Field(
        default="qwen3:4b",
        description="Ollama model name to use for AI features",
    )
    ai_request_timeout: int = Field(
        default=30,
        validation_alias=AliasChoices("AI_REQUEST_TIMEOUT", "OLLAMA_TIMEOUT"),
        description="Timeout for AI generation requests in seconds",
    )
    ollama_connect_timeout: float = Field(
        default=2.5,
        validation_alias=AliasChoices("OLLAMA_CONNECT_TIMEOUT"),
        description="Connection timeout for Ollama health checks in seconds",
    )

    @property
    def ollama_timeout(self) -> float:
        return float(self.ai_request_timeout)

    # Production Security & Monitoring
    admin_api_key: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("ADMIN_API_KEY"),
        description="Optional API key for administrative operations (cache purge, schema re-discovery)",
    )
    ai_rate_limit_per_minute: int = Field(
        default=30,
        validation_alias=AliasChoices("AI_RATE_LIMIT_PER_MINUTE"),
        description="Maximum AI chat queries per minute per client IP",
    )
    max_request_body_bytes: int = Field(
        default=1_048_576,  # 1MB
        validation_alias=AliasChoices("MAX_REQUEST_BODY_BYTES"),
        description="Maximum allowed request payload size in bytes",
    )
    enable_security_headers: bool = Field(
        default=True,
        validation_alias=AliasChoices("ENABLE_SECURITY_HEADERS"),
        description="Enable standard OWASP security response headers",
    )

    # Application Settings
    cors_origins: str = Field(
        default=(
            "https://ai-weather-intelligence-1.onrender.com,"
            "https://ai-weather-intelligence.onrender.com,"
            "http://localhost:5173,"
            "http://127.0.0.1:5173,"
            "http://localhost:3000,"
            "http://127.0.0.1:3000"
        ),
        validation_alias=AliasChoices("CORS_ORIGINS", "ALLOWED_ORIGINS"),
        description="Comma-separated list of allowed CORS origins",
    )
    cors_origin_regex: Optional[str] = Field(
        default=r"^https://ai-weather-intelligence(-\w+)?\.onrender\.com$",
        validation_alias=AliasChoices("CORS_ORIGIN_REGEX"),
        description="Regex pattern for allowed CORS origins (e.g. Render production domains)",
    )
    log_level: str = Field(
        default="INFO",
        description="Logging level",
    )
    cache_ttl_seconds: int = Field(
        default=300,
        description="Cache time-to-live in seconds",
    )

    @property
    def cors_origins_list(self) -> List[str]:
        """Parse comma-separated CORS origins into a list."""
        return [origin.strip() for origin in self.cors_origins.split(",")]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


_settings_instance: Optional[Settings] = None


def get_settings() -> Settings:
    """Get cached application settings instance."""
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = Settings()
    return _settings_instance
