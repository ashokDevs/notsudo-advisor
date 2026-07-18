from __future__ import annotations

import os
from pathlib import Path

def load_queries() -> dict[str, str]:
    """Parse queries.sql and return a dict of {name: sql}."""
    queries: dict[str, str] = {}
    
    current_dir = Path(__file__).parent
    sql_path = current_dir / "queries.sql"
    
    if not sql_path.exists():
        return queries

    with open(sql_path, "r", encoding="utf-8") as f:
        content = f.read()

    current_name = None
    current_sql: list[str] = []

    for line in content.splitlines():
        if line.startswith("-- name:"):
            if current_name is not None:
                queries[current_name] = "\n".join(current_sql).strip()
            current_name = line.split("-- name:")[1].strip()
            current_sql = []
        else:
            if current_name is not None:
                current_sql.append(line)

    if current_name is not None:
        queries[current_name] = "\n".join(current_sql).strip()

    return queries

QUERIES = load_queries()
