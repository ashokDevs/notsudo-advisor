from __future__ import annotations

from pathlib import Path

from core.analysis.pipeline import analyze_repo


async def test_repo_without_supported_manifest_reports_unsupported_status(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("Documentation only\n", encoding="utf-8")

    result = await analyze_repo(tmp_path)

    assert result["scan_status"] == "unsupported"

