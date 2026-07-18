"""create tenants, repos, advisories tables (initial)

Revision ID: 72d1bb85dfb8
Revises: 
Create Date: 2026-05-08 20:21:28.194041

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '72d1bb85dfb8'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    
    op.execute("""
        CREATE TABLE tenants (
            id UUID PRIMARY KEY,
            name TEXT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
    """)

    op.execute("""
        CREATE TABLE repos (
            id UUID PRIMARY KEY,
            tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            url TEXT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
    """)

    op.execute("""
        CREATE TABLE advisories (
            id UUID PRIMARY KEY,
            source_id TEXT UNIQUE NOT NULL,
            package_name TEXT NOT NULL,
            affected_ranges JSONB NOT NULL,
            summary TEXT NOT NULL,
            details TEXT NOT NULL,
            embedding vector(1024),
            fts TSVECTOR GENERATED ALWAYS AS (to_tsvector('english', summary || ' ' || details)) STORED
        );
    """)
    op.execute("CREATE INDEX idx_advisories_embedding ON advisories USING hnsw (embedding vector_cosine_ops);")
    op.execute("CREATE INDEX idx_advisories_fts ON advisories USING GIN (fts);")


def downgrade() -> None:
    op.execute("DROP TABLE advisories CASCADE;")
    op.execute("DROP TABLE repos CASCADE;")
    op.execute("DROP TABLE tenants CASCADE;")
    op.execute("DROP EXTENSION IF EXISTS vector;")
