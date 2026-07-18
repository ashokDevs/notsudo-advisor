from __future__ import annotations

from core.analysis.github_clone import is_github_target, parse_github_ref


def test_parse_https_url() -> None:
    assert parse_github_ref("https://github.com/expressjs/express") == ("expressjs", "express")
    assert parse_github_ref("https://github.com/expressjs/express.git") == ("expressjs", "express")


def test_parse_short_form() -> None:
    assert parse_github_ref("expressjs/express") == ("expressjs", "express")


def test_parse_ssh() -> None:
    assert parse_github_ref("git@github.com:foo/bar.git") == ("foo", "bar")


def test_is_github_target() -> None:
    assert is_github_target("https://github.com/a/b")
    assert is_github_target("a/b")
