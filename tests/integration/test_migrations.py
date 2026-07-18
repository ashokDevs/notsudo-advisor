import os

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

pytestmark = pytest.mark.asyncio

@pytest.fixture
def db_engine() -> Engine:
    url = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/notsudo")
    engine = create_engine(url)
    yield engine
    engine.dispose()

def test_up_then_down_is_clean(db_engine: Engine) -> None:
    alembic_cfg = Config("alembic.ini")
    
    # Check that we can run upgrade
    command.upgrade(alembic_cfg, "head")
    
    # Check that tables exist
    with db_engine.connect() as conn:
        res = conn.execute(text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'"))
        tables = {row[0] for row in res}
        assert "tenants" in tables
        assert "repos" in tables
        assert "advisories" in tables
        assert "code_chunks" in tables
        assert "repo_dependencies" in tables
    
    # Check that we can run downgrade
    command.downgrade(alembic_cfg, "base")
    
    # Check that tables are dropped
    with db_engine.connect() as conn:
        res = conn.execute(text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'"))
        tables = {row[0] for row in res}
        assert "tenants" not in tables
        assert "repos" not in tables
        assert "advisories" not in tables
        assert "code_chunks" not in tables
        assert "repo_dependencies" not in tables

    # Re-apply migrations so other tests have a clean schema
    command.upgrade(alembic_cfg, "head")
