from __future__ import annotations

from core.analysis.evidence import EvidenceQuote, EvidenceQuoteValidator


def test_quote_matches_normalized() -> None:
    v = EvidenceQuoteValidator()
    source = "const out = _.merge({}, userInput);"
    assert v.quote_matches(source, "_.merge({}, userInput)") is True


def test_validate_rejects_missing_source() -> None:
    v = EvidenceQuoteValidator(repo_root=None)
    ok, valid, failures = v.validate(
        [
            EvidenceQuote(
                file_path="does-not-exist.js",
                line_start=1,
                line_end=1,
                quote="totally made up quote that is not real",
            )
        ],
        file_contents={},
    )
    assert len(valid) == 0
    assert failures
    assert ok is False


def test_validate_accepts_matching_quote() -> None:
    v = EvidenceQuoteValidator()
    content = "function run() {\n  return _.merge({}, x);\n}\n"
    ok, valid, failures = v.validate(
        [
            EvidenceQuote(
                file_path="app.js",
                line_start=2,
                line_end=2,
                quote="_.merge({}, x)",
            )
        ],
        file_contents={"app.js": content},
    )
    assert ok is True
    assert len(valid) == 1
    assert not failures
