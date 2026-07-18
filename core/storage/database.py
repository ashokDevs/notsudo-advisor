from __future__ import annotations

import os
from collections.abc import AsyncGenerator
from typing import Any

import asyncpg

from core.observability.logging import get_logger

logger = get_logger(__name__)

class Database:
    def __init__(self) -> None:
        self._pool: asyncpg.Pool[asyncpg.Record] | None = None

    async def connect(self, dsn: str | None = None) -> None:
        if self._pool is not None:
            return
        
        conn_str = dsn or os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/notsudo")
        logger.info("connecting to database")
        self._pool = await asyncpg.create_pool(
            conn_str,
            min_size=1,
            max_size=10,
            command_timeout=60.0
        )

    async def disconnect(self) -> None:
        if self._pool is not None:
            logger.info("disconnecting from database")
            await self._pool.close()
            self._pool = None

    async def fetch(self, query: str, *args: Any) -> list[asyncpg.Record]:
        if self._pool is None:
            raise RuntimeError("Database not connected")
        return await self._pool.fetch(query, *args)

    async def fetchrow(self, query: str, *args: Any) -> asyncpg.Record | None:
        if self._pool is None:
            raise RuntimeError("Database not connected")
        return await self._pool.fetchrow(query, *args)

    async def execute(self, query: str, *args: Any) -> str:
        if self._pool is None:
            raise RuntimeError("Database not connected")
        return await self._pool.execute(query, *args)
