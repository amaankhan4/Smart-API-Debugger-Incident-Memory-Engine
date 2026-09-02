from app.services.ingest_service import LineBuffer


def test_complete_lines_are_returned_and_nothing_is_pending():
    buffer = LineBuffer()
    assert buffer.feed("a\nb\nc\n") == ["a", "b", "c"]
    assert buffer.pending == ""
    assert buffer.flush() == []


def test_line_split_across_chunks_is_reassembled():
    buffer = LineBuffer()

    first = buffer.feed("2024-05-01 ERROR database conn")
    assert first == []
    assert buffer.pending == "2024-05-01 ERROR database conn"

    second = buffer.feed("ection timeout\nnext line\n")
    assert second == ["2024-05-01 ERROR database conn" + "ection timeout", "next line"]


def test_trailing_line_without_newline_is_emitted_by_flush():
    buffer = LineBuffer()
    assert buffer.feed("first\nlast-without-newline") == ["first"]
    assert buffer.flush() == ["last-without-newline"]
    assert buffer.flush() == []


def test_windows_line_endings_are_normalised():
    buffer = LineBuffer()
    assert buffer.feed("alpha\r\nbeta\r\n") == ["alpha", "beta"]


def test_chunk_boundary_never_creates_a_logical_boundary():
    original = "line-one\nline-two\nline-three\nline-four"
    for split in range(1, len(original)):
        buffer = LineBuffer()
        produced = buffer.feed(original[:split])
        produced += buffer.feed(original[split:])
        produced += buffer.flush()
        assert produced == original.split("\n"), f"failed when split at {split}"


def test_empty_lines_are_preserved_for_line_numbering():
    buffer = LineBuffer()
    assert buffer.feed("a\n\nb\n") == ["a", "", "b"]
