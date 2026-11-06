import asyncio


async def test_role_and_event_isolation(client, accounts, event, event_payload):
    path = f"/api/v1/events/{event['id']}"
    for role in ("other", "staff", "audience"):
        assert (await client.get(path, headers=accounts[role]["headers"])).status_code == 404
    for role in ("admin", "client"):
        assert (await client.get(path, headers=accounts[role]["headers"])).status_code == 200
    assert (
        await client.post(
            "/api/v1/events", headers=accounts["staff"]["headers"], json=event_payload
        )
    ).status_code == 403
    added = await client.post(
        path + "/members",
        headers=accounts["admin"]["headers"],
        json={"user_id": accounts["staff"]["id"]},
    )
    assert added.status_code == 201
    assert (await client.get(path, headers=accounts["staff"]["headers"])).status_code == 200
    assert (
        await client.put(path, headers=accounts["staff"]["headers"], json=event_payload)
    ).status_code == 403
    result = await client.get("/api/v1/events", headers=accounts["other"]["headers"])
    assert result.json()["total"] == 0
    result = await client.get("/api/v1/events", headers=accounts["staff"]["headers"])
    assert result.json()["total"] == 1
    removed = await client.delete(
        path + f"/members/{accounts['staff']['id']}", headers=accounts["admin"]["headers"]
    )
    assert removed.status_code == 204
    assert (await client.get(path, headers=accounts["staff"]["headers"])).status_code == 404


async def test_lifecycle_and_concurrent_transition(client, accounts, event, event_payload):
    path = f"/api/v1/events/{event['id']}"
    assert (
        await client.patch(
            path + "/status", headers=accounts["client"]["headers"], json={"status": "completed"}
        )
    ).status_code == 409
    assert (
        await client.patch(
            path + "/status", headers=accounts["client"]["headers"], json={"status": "submitted"}
        )
    ).status_code == 200
    assert (
        await client.put(path, headers=accounts["client"]["headers"], json=event_payload)
    ).status_code == 409
    assert (
        await client.patch(
            path + "/status", headers=accounts["client"]["headers"], json={"status": "approved"}
        )
    ).status_code == 403
    results = await asyncio.gather(
        *[
            client.patch(
                path + "/status", headers=accounts["admin"]["headers"], json={"status": "approved"}
            )
            for _ in range(2)
        ]
    )
    assert sorted(r.status_code for r in results) == [200, 409]


async def test_validation_agenda_and_pagination(client, accounts, event, event_payload):
    for bad in (
        {"total_budget": 10.5},
        {"total_budget": "-1"},
        {"total_budget": "NaN"},
        {"starts_at": "2027-01-02T09:00:00"},
        {"ends_at": "2026-01-01T00:00:00Z"},
    ):
        response = await client.post(
            "/api/v1/events", headers=accounts["client"]["headers"], json={**event_payload, **bad}
        )
        assert response.status_code == 422, response.text
    agenda = {
        "title": "Opening",
        "starts_at": "2027-01-02T10:00:00+05:30",
        "ends_at": "2027-01-02T11:00:00+05:30",
    }
    path = f"/api/v1/events/{event['id']}/agenda"
    assert (
        await client.post(path, headers=accounts["client"]["headers"], json=agenda)
    ).status_code == 201
    agenda["ends_at"] = "2027-01-03T11:00:00+05:30"
    assert (
        await client.post(path, headers=accounts["client"]["headers"], json=agenda)
    ).status_code == 422
    response = await client.get(
        "/api/v1/events?page_size=101", headers=accounts["admin"]["headers"]
    )
    assert response.status_code == 422


async def test_health_and_openapi(client):
    assert (await client.get("/health/live")).status_code == 200
    assert (await client.get("/health/ready")).status_code == 200
    contract = (await client.get("/openapi.json")).json()
    assert "/api/v1/events/{event_id}/expenses" in contract["paths"]


async def test_draft_edits_preserve_budget_currency_and_agenda(
    client, accounts, event, event_payload
):
    path = f"/api/v1/events/{event['id']}"
    owner = accounts["client"]["headers"]
    budget = await client.post(
        path + "/budget-lines",
        headers={
            **owner,
            "Idempotency-Key": "allocate",
        },
        json={"title": "Venue", "amount": "600.00"},
    )
    assert budget.status_code == 201
    for patch in ({"total_budget": "500.00"}, {"currency": "USD"}):
        result = await client.put(path, headers=owner, json={**event_payload, **patch})
        assert result.status_code == 409
    result = await client.put(path, headers=owner, json={**event_payload, "title": "Changed title"})
    assert result.status_code == 200
    agenda = await client.post(
        path + "/agenda",
        headers=owner,
        json={
            "title": "Welcome",
            "starts_at": "2027-01-02T09:00:00+05:30",
            "ends_at": "2027-01-02T10:00:00+05:30",
        },
    )
    assert agenda.status_code == 201
    result = await client.put(
        path,
        headers=owner,
        json={
            **event_payload,
            "starts_at": "2027-01-02T10:00:00+05:30",
        },
    )
    assert result.status_code == 409
