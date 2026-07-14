"""Run all PostgreSQL schema setup required by Script Chat."""
from __future__ import annotations

import asyncio
from pathlib import Path

from alembic import command
from alembic.config import Config
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from src.script_chat.persistence import get_database_url


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def migrate_application_schema() -> None:
    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    command.upgrade(config, "head")


async def migrate_checkpoint_schema() -> None:
    async with AsyncPostgresSaver.from_conn_string(get_database_url()) as saver:
        await saver.setup()


def main() -> None:
    migrate_application_schema()
    asyncio.run(migrate_checkpoint_schema())


if __name__ == "__main__":
    main()
