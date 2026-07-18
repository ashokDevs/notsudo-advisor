"""create code_chunks, repo_dependencies tables

Revision ID: 273fbcd1fedc
Revises: 72d1bb85dfb8
Create Date: 2026-05-08 20:29:23.598688

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '273fbcd1fedc'
down_revision: Union[str, Sequence[str], None] = '72d1bb85dfb8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE code_chunks (
            id UUID PRIMARY KEY,
            repo_id UUID NOT NULL REFERENCES repos(id) ON DELETE CASCADE,
            commit_sha TEXT NOT NULL,
            file_path TEXT NOT NULL,
            start_line INT NOT NULL,
            end_line INT NOT NULL,
            symbol TEXT,
            content TEXT NOT NULL,
            content_hash TEXT NOT NULL,
            embedding vector(1024),
            fts TSVECTOR GENERATED ALWAYS AS (to_tsvector('english', coalesce(symbol, '') || ' ' || content)) STORED
        );
    """)
    op.execute("CREATE INDEX idx_code_chunks_repo_commit ON code_chunks(repo_id, commit_sha);")
    op.execute("CREATE INDEX idx_code_chunks_embedding ON code_chunks USING hnsw (embedding vector_cosine_ops);")
    op.execute("CREATE INDEX idx_code_chunks_fts ON code_chunks USING GIN (fts);")

    op.execute("""
        CREATE TABLE repo_dependencies (
            id UUID PRIMARY KEY,
            repo_id UUID NOT NULL REFERENCES repos(id) ON DELETE CASCADE,
            commit_sha TEXT NOT NULL,
            package_name TEXT NOT NULL,
            declared_version TEXT NOT NULL,
            resolved_version TEXT NOT NULL
        );
    """)
    op.execute("CREATE INDEX idx_repo_deps_repo_commit ON repo_dependencies(repo_id, commit_sha);")


def downgrade() -> None:
    op.execute("DROP TABLE repo_dependencies CASCADE;")
    op.execute("DROP TABLE code_chunks CASCADE;")
