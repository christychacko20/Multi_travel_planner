from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from psycopg import AsyncConnection
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from app.config import get_settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS workflow_runs (
    run_id TEXT PRIMARY KEY,
    task TEXT NOT NULL,
    status TEXT NOT NULL,
    state JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""


@asynccontextmanager
async def connection() -> AsyncIterator[AsyncConnection[Any]]:
    async with await AsyncConnection.connect(
        get_settings().database_url, row_factory=dict_row
    ) as conn:
        yield conn


async def initialise_database() -> None:
    async with connection() as conn:
        await conn.execute(SCHEMA)
        await conn.commit()


async def save_run(run_id: str, task: str, status: str, state: dict[str, Any]) -> None:
    async with connection() as conn:
        await conn.execute(
            """
            INSERT INTO workflow_runs (run_id, task, status, state)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (run_id) DO UPDATE SET
                status = EXCLUDED.status,
                state = EXCLUDED.state,
                updated_at = NOW()
            """,
            (run_id, task, status, Jsonb(state)),
        )
        await conn.commit()
