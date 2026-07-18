from __future__ import annotations

from pathlib import Path

from core.analysis.call_sites import CallSiteFinder


def test_finds_lodash_import_and_merge_call(tmp_path: Path) -> None:
    src = tmp_path / "src"
    src.mkdir()
    (src / "app.js").write_text(
        "const _ = require('lodash');\n"
        "function run(user) {\n"
        "  return _.merge({}, user);\n"
        "}\n",
        encoding="utf-8",
    )
    finder = CallSiteFinder()
    sites = finder.find(tmp_path, "lodash", symbols=["merge"])
    kinds = {s.kind for s in sites}
    assert "require" in kinds or "import" in kinds
    assert any(s.kind == "call" for s in sites)
