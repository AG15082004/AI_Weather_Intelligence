"""Database connection pool manager.

Provides connection management and reuse to Microsoft Fabric SQL via
FabricConnectionService.
"""

from typing import Any, Dict, Optional

import pyodbc
import structlog

from app.services.fabric_connection import FabricConnectionService

log = structlog.get_logger()


class ConnectionPool:
    """Connection manager for Fabric SQL.

    Reuses an active pyodbc connection with health checks and reconnection.
    """

    def __init__(self, fabric_service: Optional[FabricConnectionService] = None) -> None:
        self._fabric_service = fabric_service or FabricConnectionService()

    async def get_connection(self) -> pyodbc.Connection:
        """Get an active database connection.

        Returns an existing connection if alive, otherwise opens a new one.

        Returns:
            An active pyodbc.Connection.
        """
        return await self._fabric_service.connect()

    async def close(self) -> None:
        """Close the active connection."""
        await self._fabric_service.disconnect()

    async def health_check(self) -> Dict[str, Any]:
        """Verify connection pool health by executing SELECT 1 AS connection_status."""
        return await self._fabric_service.verify_connection()


_pool_instance: Optional[ConnectionPool] = None


def get_pool() -> ConnectionPool:
    """Get the singleton ConnectionPool instance."""
    global _pool_instance
    if _pool_instance is None:
        _pool_instance = ConnectionPool()
    return _pool_instance
