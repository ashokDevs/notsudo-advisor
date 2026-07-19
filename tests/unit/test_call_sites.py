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


def test_ignores_code_shaped_files_inside_git_metadata(tmp_path: Path) -> None:
    source = tmp_path / "src"
    source.mkdir()
    (source / "app.js").write_text("const express = require('express');\n", encoding="utf-8")
    git_objects = tmp_path / ".git" / "objects"
    git_objects.mkdir(parents=True)
    (git_objects / "packed.js").write_text("const express = require('express');\n", encoding="utf-8")

    sites = CallSiteFinder().find(tmp_path, "express")

    assert [site.file_path for site in sites] == ["src/app.js"]
