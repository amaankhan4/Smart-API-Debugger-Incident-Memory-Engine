from datetime import timezone

from app.schemas.enums import ErrorCategory, Level
from app.services.parser import classify_error, parse_log_line, parse_timestamp


def test_blank_lines_are_skipped():
    assert parse_log_line("") is None
    assert parse_log_line("   \n") is None


def test_plain_format_extracts_level_service_and_message():
    parsed = parse_log_line("2024-05-01T10:00:00Z ERROR auth-service Database connection timeout")

    assert parsed is not None
    assert parsed["level"] == Level.ERROR.value
    assert parsed["service"] == "auth-service"
    assert "Database connection timeout" in parsed["message"]
    assert parsed["timestamp"].tzinfo is not None


def test_bracketed_format_with_key_value_metadata():
    parsed = parse_log_line(
        "[2024-05-01 10:00:00] WARNING service=payments trace_id=abc123 span_id=s-9 Retry scheduled"
    )

    assert parsed is not None
    assert parsed["level"] == Level.WARN.value
    assert parsed["service"] == "payments"
    assert parsed["trace_id"] == "abc123"
    assert parsed["span_id"] == "s-9"


def test_python_logging_default_format():
    """logging.basicConfig emits "<ts> - <LEVEL> - <message>" with comma milliseconds."""
    parsed = parse_log_line("2026-03-24 11:00:42,268 - ERROR - Gen_AI: OpenAI call failed")

    assert parsed is not None
    assert parsed["level"] == Level.ERROR.value
    assert parsed["message"] == "Gen_AI: OpenAI call failed"
    assert parsed["timestamp"].isoformat() == "2026-03-24T11:00:42.268000+00:00"


def test_python_logging_format_with_logger_name():
    parsed = parse_log_line("2026-03-24 11:00:42,268 - my.module - WARNING - Retry scheduled")

    assert parsed is not None
    assert parsed["level"] == Level.WARN.value
    assert parsed["service"] == "my.module"
    assert parsed["message"] == "Retry scheduled"


def test_pipe_delimited_format():
    parsed = parse_log_line("2024-05-01 10:00:00 | INFO | checkout | Order placed")

    assert parsed is not None
    assert parsed["level"] == Level.INFO.value
    assert parsed["service"] == "checkout"
    assert parsed["message"] == "Order placed"


def test_delimited_line_without_a_level_still_keeps_its_timestamp():
    parsed = parse_log_line("2024-05-01 10:00:00 - starting up without a level token")

    assert parsed is not None
    assert parsed["timestamp"] is not None
    assert parsed["message"] == "starting up without a level token"


def test_iso_timestamp_is_not_split_on_its_own_dashes():
    parsed = parse_log_line("2024-05-01T10:00:00Z ERROR auth-service Database connection timeout")

    assert parsed is not None
    assert parsed["service"] == "auth-service"


def test_json_logs_are_parsed_natively():
    line = (
        '{"timestamp":"2024-05-01T10:00:00Z","level":"error","service":"checkout",'
        '"message":"Payment declined","trace_id":"t-42","status":502,"method":"POST","path":"/api/pay"}'
    )
    parsed = parse_log_line(line)

    assert parsed is not None
    assert parsed["level"] == Level.ERROR.value
    assert parsed["service"] == "checkout"
    assert parsed["trace_id"] == "t-42"
    assert parsed["status_code"] == 502
    assert parsed["http_method"] == "POST"
    assert parsed["path"] == "/api/pay"
    assert parsed["error_category"] == ErrorCategory.DEPENDENCY.value


def test_http_details_are_extracted_from_free_text():
    parsed = parse_log_line("2024-05-01T10:00:00Z ERROR api POST /api/login failed with 500")

    assert parsed is not None
    assert parsed["http_method"] == "POST"
    assert parsed["path"] == "/api/login"
    assert parsed["status_code"] == 500


def test_exception_and_category_detection():
    parsed = parse_log_line(
        "2024-05-01T10:00:00Z ERROR orders java.sql.SQLTimeoutException connection pool exhausted"
    )

    assert parsed is not None
    assert parsed["exception"] == "java.sql.SQLTimeoutException"
    assert parsed["error_category"] == ErrorCategory.TIMEOUT.value


def test_unparseable_line_is_kept_not_dropped():
    parsed = parse_log_line("<<< totally unstructured payload >>>")

    assert parsed is not None
    assert parsed["message"] == "<<< totally unstructured payload >>>"
    assert parsed["service"] == "unknown"
    assert parsed["level"] == Level.INFO.value


def test_missing_fields_are_null_not_invented():
    parsed = parse_log_line("2024-05-01T10:00:00Z INFO worker Job finished")

    assert parsed is not None
    assert parsed["trace_id"] is None
    assert parsed["status_code"] is None
    assert parsed["path"] is None
    assert parsed["error_category"] == ErrorCategory.UNKNOWN.value


def test_non_error_levels_are_not_categorised_as_failures():
    parsed = parse_log_line("2024-05-01T10:00:00Z INFO db Connected to database")

    assert parsed is not None
    assert parsed["error_category"] == ErrorCategory.UNKNOWN.value


def test_parse_timestamp_normalises_to_utc():
    assert parse_timestamp("2024-05-01T10:00:00Z").tzinfo == timezone.utc
    assert parse_timestamp("2024-05-01 10:00:00").tzinfo == timezone.utc
    assert parse_timestamp("not-a-date") is None
    assert parse_timestamp(None) is None


def test_classify_error_uses_status_code_fallback():
    assert classify_error("something odd", None, 429) == ErrorCategory.RATE_LIMIT
    assert classify_error("something odd", None, 403) == ErrorCategory.AUTHORIZATION
    assert classify_error("nothing notable", None, None) == ErrorCategory.UNKNOWN


def test_parser_never_raises_on_hostile_input():
    for line in ("{" * 500, "\x00\x01binary", "a" * 20000, '{"level":'):
        assert parse_log_line(line) is not None
