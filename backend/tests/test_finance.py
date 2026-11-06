import asyncio


async def test_idempotent_expenses_and_conflicting_payload(client, accounts, event):
    path = f"/api/v1/events/{event['id']}/expenses"
    headers = {**accounts["client"]["headers"], "Idempotency-Key": "expense-1"}
    data = {"description": "Flowers", "amount": "100.00"}
    results = await asyncio.gather(
        *[client.post(path, json=data, headers=headers) for _ in range(2)]
    )
    assert [r.status_code for r in results] == [201, 201]
    assert results[0].json() == results[1].json()
    assert (await client.get(path, headers=accounts["client"]["headers"])).json()["total"] == 1
    changed = await client.post(path, json={**data, "amount": "101.00"}, headers=headers)
    assert changed.status_code == 409
    assert (
        await client.post(path, json=data, headers=accounts["client"]["headers"])
    ).status_code == 422


async def test_concurrent_budget_cannot_overallocate(client, accounts, event):
    path = f"/api/v1/events/{event['id']}/budget-lines"
    results = await asyncio.gather(
        *[
            client.post(
                path,
                json={"title": "Food", "amount": "600.00"},
                headers={
                    **accounts["admin"]["headers"],
                    "Idempotency-Key": f"budget-{i}",
                },
            )
            for i in range(2)
        ]
    )
    assert sorted(r.status_code for r in results) == [201, 409]
    assert (await client.get(path, headers=accounts["client"]["headers"])).json()["total"] == 1


async def test_review_settlement_and_closed_finances(client, accounts, event):
    path = f"/api/v1/events/{event['id']}"
    submitted = await client.post(
        path + "/expenses",
        json={"description": "Venue", "amount": "100.10"},
        headers={
            **accounts["client"]["headers"],
            "Idempotency-Key": "expense",
        },
    )
    expense_id = submitted.json()["id"]
    review_path = path + f"/expenses/{expense_id}"
    assert (
        await client.patch(
            review_path, json={"status": "approved"}, headers=accounts["client"]["headers"]
        )
    ).status_code == 403
    admin = {**accounts["admin"]["headers"], "Idempotency-Key": "settle"}
    assert (await client.post(path + "/settlements", headers=admin)).status_code == 409
    for status in ("submitted", "approved", "in_progress", "completed"):
        response = await client.patch(
            path + "/status", json={"status": status}, headers=accounts["admin"]["headers"]
        )
        assert response.status_code == 200, response.text
    assert (await client.post(path + "/settlements", headers=admin)).status_code == 409
    approved = await client.patch(
        review_path, json={"status": "approved"}, headers=accounts["admin"]["headers"]
    )
    assert approved.status_code == 200, approved.text
    assert (
        await client.patch(
            review_path, json={"status": "approved"}, headers=accounts["admin"]["headers"]
        )
    ).status_code == 409
    summary = await client.get(path + "/settlements/summary", headers=accounts["client"]["headers"])
    assert summary.json()["remaining_budget"] == "899.90"
    finalized = await client.post(path + "/settlements", headers=admin)
    assert finalized.status_code == 201, finalized.text
    assert finalized.json()["approved_expenses"] == "100.10"
    replay = await client.post(path + "/settlements", headers=admin)
    assert replay.json() == finalized.json()
    changed = await client.patch(
        review_path, json={"status": "rejected"}, headers=accounts["admin"]["headers"]
    )
    assert changed.status_code == 409


async def test_finance_scope_staff_visibility_and_self_review(client, accounts, event):
    path = f"/api/v1/events/{event['id']}"
    for suffix in ("/budget-lines", "/expenses", "/settlements/summary"):
        denied = await client.get(path + suffix, headers=accounts["other"]["headers"])
        assert denied.status_code == 404
    member = await client.post(
        path + "/members",
        headers=accounts["admin"]["headers"],
        json={
            "user_id": accounts["staff"]["id"],
        },
    )
    assert member.status_code == 201
    ids = {}
    for name in ("client", "staff", "admin"):
        expense = await client.post(
            path + "/expenses",
            headers={
                **accounts[name]["headers"],
                "Idempotency-Key": "new-expense",
            },
            json={"description": "Materials", "amount": "20.00"},
        )
        assert expense.status_code == 201
        ids[name] = expense.json()["id"]
    staff_list = await client.get(path + "/expenses", headers=accounts["staff"]["headers"])
    assert staff_list.json()["total"] == 1
    assert staff_list.json()["items"][0]["id"] == ids["staff"]
    assert (
        await client.get(path + "/budget-lines", headers=accounts["staff"]["headers"])
    ).status_code == 403
    review = await client.patch(
        path + f"/expenses/{ids['admin']}",
        headers=accounts["admin"]["headers"],
        json={"status": "approved"},
    )
    assert review.status_code == 403
