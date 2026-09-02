"""Ingestion + ownership isolation across the real HTTP surface."""


async def _upload_and_ingest(client, headers, content: bytes, filename: str = "app.log"):
    upload = await client.post(
        "/api/v1/files", headers=headers, files={"file": (filename, content, "text/plain")}
    )
    assert upload.status_code == 201, upload.text
    file_id = upload.json()["file_id"]

    ingest = await client.post(f"/api/v1/ingest/{file_id}", headers=headers)
    assert ingest.status_code == 200, ingest.text
    return file_id, ingest.json()


async def test_upload_then_ingest_creates_structured_events(client, make_user, sample_log):
    user = await make_user()
    file_id, result = await _upload_and_ingest(client, user["headers"], sample_log)

    assert result["events_created"] == 4
    assert result["chunks_processed"] >= 1

    events = await client.get(
        "/api/v1/events", headers=user["headers"], params={"file_id": file_id}
    )
    assert events.status_code == 200
    body = events.json()
    assert body["total"] == 4

    services = {item["service"] for item in body["items"]}
    assert "auth-service" in services
    assert all(item["user_id"] == user["user"]["id"] for item in body["items"])


async def test_error_events_are_counted_and_filterable(client, make_user, sample_log):
    user = await make_user()
    await _upload_and_ingest(client, user["headers"], sample_log)

    errors = await client.get(
        "/api/v1/events", headers=user["headers"], params={"only_errors": "true"}
    )
    assert errors.status_code == 200
    assert errors.json()["total"] == 2


async def test_line_numbers_are_sequential_and_unique(client, make_user, sample_log):
    user = await make_user()
    await _upload_and_ingest(client, user["headers"], sample_log)

    response = await client.get(
        "/api/v1/events", headers=user["headers"], params={"limit": 100}
    )
    line_numbers = sorted(item["line_no"] for item in response.json()["items"])
    assert line_numbers == [1, 2, 3, 4]


async def test_reingest_is_idempotent(client, make_user, sample_log):
    user = await make_user()
    file_id, _ = await _upload_and_ingest(client, user["headers"], sample_log)

    again = await client.post(
        f"/api/v1/ingest/{file_id}", headers=user["headers"], params={"force": "true"}
    )
    assert again.status_code == 200

    events = await client.get("/api/v1/events", headers=user["headers"])
    assert events.json()["total"] == 4  # not duplicated


async def test_only_events_above_the_level_floor_are_queued_for_embedding(client, make_user):
    """Quiet lines stay searchable in Mongo but never spend vector-store budget."""
    user = await make_user()
    log = (
        b"2024-05-01T10:00:00Z INFO auth-service User login succeeded\n"
        b"2024-05-01T10:00:01Z DEBUG auth-service Cache hit for session\n"
        b"2024-05-01T10:00:02Z ERROR auth-service Database connection timeout\n"
    )
    await _upload_and_ingest(client, user["headers"], log, filename="levels.log")

    response = await client.get("/api/v1/events", headers=user["headers"])
    statuses = {item["level"]: item["embedding_status"] for item in response.json()["items"]}
    assert statuses == {"INFO": "skipped", "DEBUG": "skipped", "ERROR": "queued"}


async def test_file_with_nothing_to_embed_completes(client, make_user):
    """Only the embedding worker leaves EMBEDDING, so such a file must complete at ingest."""
    user = await make_user()
    log = b"2024-05-01T10:00:00Z INFO auth-service User login succeeded\n"
    file_id, _ = await _upload_and_ingest(client, user["headers"], log, filename="quiet.log")

    response = await client.get(f"/api/v1/files/{file_id}", headers=user["headers"])
    assert response.json()["status"] == "completed"


async def test_unsupported_extension_is_rejected(client, make_user):
    user = await make_user()
    response = await client.post(
        "/api/v1/files",
        headers=user["headers"],
        files={"file": ("payload.exe", b"binary", "application/octet-stream")},
    )
    assert response.status_code == 415


async def test_empty_file_is_rejected(client, make_user):
    user = await make_user()
    response = await client.post(
        "/api/v1/files", headers=user["headers"], files={"file": ("empty.log", b"", "text/plain")}
    )
    assert response.status_code == 400


async def test_malicious_filename_is_sanitised(client, make_user, sample_log):
    user = await make_user()
    response = await client.post(
        "/api/v1/files",
        headers=user["headers"],
        files={"file": ("../../../../etc/passwd.log", sample_log, "text/plain")},
    )

    assert response.status_code == 201
    stored = response.json()["filename"]
    assert ".." not in stored
    assert "/" not in stored and "\\" not in stored


async def test_one_user_cannot_see_another_users_events(client, make_user, sample_log):
    owner = await make_user("owner@example.com")
    intruder = await make_user("intruder@example.com")

    await _upload_and_ingest(client, owner["headers"], sample_log)

    owner_events = await client.get("/api/v1/events", headers=owner["headers"])
    intruder_events = await client.get("/api/v1/events", headers=intruder["headers"])

    assert owner_events.json()["total"] == 4
    assert intruder_events.json()["total"] == 0


async def test_one_user_cannot_see_another_users_files(client, make_user, sample_log):
    owner = await make_user("owner2@example.com")
    intruder = await make_user("intruder2@example.com")

    file_id, _ = await _upload_and_ingest(client, owner["headers"], sample_log)

    assert (await client.get("/api/v1/files", headers=intruder["headers"])).json()["total"] == 0
    assert (
        await client.get(f"/api/v1/files/{file_id}", headers=intruder["headers"])
    ).status_code == 404


async def test_one_user_cannot_ingest_another_users_file(client, make_user, sample_log):
    owner = await make_user("owner3@example.com")
    intruder = await make_user("intruder3@example.com")

    upload = await client.post(
        "/api/v1/files",
        headers=owner["headers"],
        files={"file": ("app.log", sample_log, "text/plain")},
    )
    file_id = upload.json()["file_id"]

    response = await client.post(f"/api/v1/ingest/{file_id}", headers=intruder["headers"])
    assert response.status_code == 404


async def test_one_user_cannot_read_another_users_event_detail(client, make_user, sample_log):
    owner = await make_user("owner4@example.com")
    intruder = await make_user("intruder4@example.com")

    await _upload_and_ingest(client, owner["headers"], sample_log)
    event_id = (await client.get("/api/v1/events", headers=owner["headers"])).json()["items"][0]["id"]

    assert (
        await client.get(f"/api/v1/events/{event_id}", headers=intruder["headers"])
    ).status_code == 404
    assert (
        await client.get(f"/api/v1/events/{event_id}/context", headers=intruder["headers"])
    ).status_code == 404


async def test_deleting_a_file_removes_its_events(client, make_user, sample_log):
    user = await make_user()
    file_id, _ = await _upload_and_ingest(client, user["headers"], sample_log)

    deleted = await client.delete(f"/api/v1/files/{file_id}", headers=user["headers"])
    assert deleted.status_code == 200

    events = await client.get("/api/v1/events", headers=user["headers"])
    assert events.json()["total"] == 0


async def test_event_context_marks_the_selected_event(client, make_user, sample_log):
    user = await make_user()
    await _upload_and_ingest(client, user["headers"], sample_log)

    events = (await client.get("/api/v1/events", headers=user["headers"])).json()["items"]
    target = next(item for item in events if item["line_no"] == 2)

    context = await client.get(f"/api/v1/events/{target['id']}/context", headers=user["headers"])
    assert context.status_code == 200

    body = context.json()
    assert body["event"]["id"] == target["id"]
    surrounding_ids = {item["id"] for item in body["before"] + body["after"]}
    assert target["id"] not in surrounding_ids
