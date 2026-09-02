from pathlib import Path

import pytest

from app.core.vector_db import build_filter, similarity_from_score
from app.services.search import escape_regex, explain_match
from app.utils.paths import resolve_within, sanitize_filename


@pytest.mark.parametrize(
    "raw",
    [
        "../../../etc/passwd",
        "..\\..\\windows\\system32\\config.log",
        "/absolute/path/app.log",
        "C:\\Users\\victim\\secret.log",
    ],
)
def test_sanitize_filename_strips_traversal(raw):
    cleaned = sanitize_filename(raw)
    assert ".." not in cleaned
    assert "/" not in cleaned and "\\" not in cleaned


def test_sanitize_filename_handles_blank_and_hostile_names():
    assert sanitize_filename("") == "upload.log"
    assert sanitize_filename("...") == "upload.log"
    assert len(sanitize_filename("a" * 500 + ".log")) <= 120


def test_resolve_within_blocks_escape(tmp_path: Path):
    assert resolve_within(tmp_path, "file.log").parent == tmp_path.resolve()
    with pytest.raises(ValueError):
        resolve_within(tmp_path, "../outside.log")


def test_similarity_from_score_is_bounded():
    # Upstash reports cosine as (1 + cos) / 2, so 1.0 is identical and 0.5 is orthogonal.
    assert similarity_from_score(1.0) == 1.0
    assert similarity_from_score(0.5) == 0.0
    assert similarity_from_score(0.0) == 0.0
    assert similarity_from_score(None) == 0.0
    assert 0.0 <= similarity_from_score(0.75) <= 1.0


def test_build_filter_strips_expression_injection():
    hostile = build_filter({"user_id": "abc' OR user_id != 'abc"})
    assert hostile == "user_id = 'abc OR user_id  abc'"
    assert "'" not in hostile[len("user_id = '") : -1]


def test_build_filter_skips_empty_values():
    assert build_filter({"user_id": "u1", "service": None, "file_id": ""}) == "user_id = 'u1'"


def test_escape_regex_neutralises_injection():
    escaped = escape_regex(".*(a+)+$")
    assert "\\" in escaped
    assert escaped != ".*(a+)+$"


def test_explain_match_reports_only_real_overlap():
    event = {"service": "auth-service", "exception": "DatabaseTimeout", "status_code": 500, "path": "/api/login"}

    reasons = explain_match("auth-service database timeout 500", event)
    assert any("service:auth-service" in reason for reason in reasons)
    assert any("status:500" in reason for reason in reasons)

    assert explain_match("completely unrelated query", event) == []
