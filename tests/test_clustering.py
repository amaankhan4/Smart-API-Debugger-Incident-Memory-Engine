from app.schemas.enums import IncidentSeverity
from app.services.clustering import (
    build_title,
    cluster_signature,
    derive_severity,
    normalize_message,
)


def _doc(**overrides):
    base = {
        "_id": "1",
        "service": "auth-service",
        "level": "ERROR",
        "message": "Database connection timeout",
        "error_category": "timeout",
        "exception": "DatabaseTimeout",
    }
    base.update(overrides)
    return base


def test_normalize_message_collapses_volatile_tokens():
    a = normalize_message("Timeout after 1234ms for user 550e8400-e29b-41d4-a716-446655440000")
    b = normalize_message("Timeout after 99ms for user 550e8400-e29b-41d4-a716-446655440001")
    assert a == b


def test_normalize_message_keeps_distinct_failures_distinct():
    assert normalize_message("Database timeout") != normalize_message("Payment declined")


def test_cluster_signature_is_stable_as_the_cluster_grows():
    small = [_doc() for _ in range(3)]
    grown = [_doc() for _ in range(40)]
    # Signature must depend on the symptom, not the member count, or re-runs duplicate incidents.
    assert cluster_signature(small) == cluster_signature(grown)


def test_cluster_signature_differs_for_different_symptoms():
    timeouts = [_doc() for _ in range(3)]
    declines = [_doc(message="Payment declined", exception="PaymentError", error_category="validation")]
    assert cluster_signature(timeouts) != cluster_signature(declines)


def test_severity_escalates_with_critical_level():
    assert derive_severity([_doc(level="CRITICAL")]) is IncidentSeverity.CRITICAL


def test_severity_scales_with_volume():
    assert derive_severity([_doc() for _ in range(60)]) is IncidentSeverity.HIGH
    assert derive_severity([_doc() for _ in range(12)]) is IncidentSeverity.MEDIUM
    assert derive_severity([_doc(level="WARN", status_code=None)]) is IncidentSeverity.LOW


def test_title_mentions_the_exception_and_service():
    title = build_title([_doc() for _ in range(3)])
    assert "DatabaseTimeout" in title
    assert "auth-service" in title


def test_title_falls_back_to_message_without_exception():
    docs = [_doc(exception=None, message="Upstream gateway unavailable") for _ in range(3)]
    assert "Upstream gateway unavailable" in build_title(docs)
