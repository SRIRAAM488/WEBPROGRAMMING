"""Tests for BillBell: CRUD, validation, payment and summaries."""

from datetime import date, timedelta

TODAY = date.today()


def make_bill(client, **overrides):
    """Helper that creates a bill with sensible defaults."""
    payload = {
        "bill_name": "Electricity Bill",
        "category": "electricity",
        "provider": "DemoPower",
        "amount": "1250.00",
        "currency": "INR",
        "due_date": (TODAY + timedelta(days=5)).isoformat(),
    }
    payload.update(overrides)
    return client.post("/api/bills", json=payload)


# --------------------------------------------------------------------- create


def test_create_bill_returns_201(client):
    response = make_bill(client)
    assert response.status_code == 201
    body = response.json()
    assert body["bill_name"] == "Electricity Bill"
    assert body["status"] == "unpaid"
    assert body["category_label"] == "Electricity"
    assert body["days_until_due"] == 5


def test_create_bill_rejects_negative_amount(client):
    response = make_bill(client, amount="-100")
    assert response.status_code == 422
    assert "fields" in response.json()


def test_create_bill_rejects_zero_amount(client):
    assert make_bill(client, amount="0").status_code == 422


def test_create_bill_rejects_unknown_category(client):
    assert make_bill(client, category="crypto").status_code == 422


def test_create_bill_rejects_unknown_currency(client):
    assert make_bill(client, currency="XYZ").status_code == 422


def test_create_bill_rejects_missing_name(client):
    payload = {"amount": "10", "due_date": TODAY.isoformat()}
    assert client.post("/api/bills", json=payload).status_code == 422


def test_create_bill_normalises_currency_and_text(client):
    response = make_bill(client, currency="inr", bill_name="  Trimmed  ")
    body = response.json()
    assert body["currency"] == "INR"
    assert body["bill_name"] == "Trimmed"


# ----------------------------------------------------------------------- read


def test_get_bill_by_id(client):
    bill_id = make_bill(client).json()["id"]
    response = client.get(f"/api/bills/{bill_id}")
    assert response.status_code == 200
    assert response.json()["id"] == bill_id


def test_get_missing_bill_returns_404(client):
    response = client.get("/api/bills/424242")
    assert response.status_code == 404
    assert response.json()["success"] is False


def test_summary_route_is_not_treated_as_an_id(client):
    """/summary must be matched as a fixed route, never as a bill id."""
    assert client.get("/api/bills/summary").status_code == 200


def test_list_bills_supports_search(client):
    make_bill(client, bill_name="Electricity Bill", provider="DemoPower")
    make_bill(client, bill_name="Internet Bill", provider="DemoNet")

    by_name = client.get("/api/bills", params={"search": "Internet"})
    assert by_name.json()["total"] == 1
    assert by_name.json()["items"][0]["bill_name"] == "Internet Bill"

    by_provider = client.get("/api/bills", params={"search": "DemoNet"})
    assert by_provider.json()["total"] == 1


def test_list_bills_filters_by_category_and_status(client):
    make_bill(client, category="electricity", bill_name="A")
    make_bill(client, category="internet", bill_name="B")
    make_bill(client, category="internet", bill_name="C", status="paid")

    assert client.get("/api/bills", params={"category": "internet"}).json()["total"] == 2
    assert client.get("/api/bills", params={"status": "paid"}).json()["total"] == 1
    assert client.get("/api/bills", params={"status": "all"}).json()["total"] == 3


def test_list_bills_sorts_and_paginates(client):
    make_bill(client, bill_name="Soon", amount="10", due_date=(TODAY + timedelta(days=1)).isoformat())
    make_bill(client, bill_name="Later", amount="20", due_date=(TODAY + timedelta(days=9)).isoformat())
    make_bill(client, bill_name="Big", amount="999", due_date=(TODAY + timedelta(days=5)).isoformat())

    by_due = client.get("/api/bills", params={"sort_by": "due_date", "sort_order": "asc"}).json()
    assert [b["bill_name"] for b in by_due["items"]] == ["Soon", "Big", "Later"]

    by_amount = client.get("/api/bills", params={"sort_by": "amount", "sort_order": "desc"}).json()
    assert by_amount["items"][0]["bill_name"] == "Big"

    page = client.get("/api/bills", params={"page": 1, "page_size": 2}).json()
    assert len(page["items"]) == 2
    assert page["total"] == 3
    assert page["total_pages"] == 2


# ---------------------------------------------------------------------- edit


def test_patch_bill_updates_only_given_fields(client):
    bill_id = make_bill(client).json()["id"]
    response = client.patch(f"/api/bills/{bill_id}", json={"amount": "999.50"})
    assert response.status_code == 200
    body = response.json()
    assert body["amount"] == "999.50"
    assert body["bill_name"] == "Electricity Bill"  # untouched


def test_patch_rejects_negative_amount(client):
    bill_id = make_bill(client).json()["id"]
    assert client.patch(f"/api/bills/{bill_id}", json={"amount": "-1"}).status_code == 422


def test_delete_bill(client):
    bill_id = make_bill(client).json()["id"]
    assert client.delete(f"/api/bills/{bill_id}").status_code == 200
    assert client.get(f"/api/bills/{bill_id}").status_code == 404


# ------------------------------------------------------------------- payment


def test_pay_bill_records_date_and_status(client):
    bill_id = make_bill(client).json()["id"]
    response = client.post(f"/api/bills/{bill_id}/pay", json={})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "paid"
    assert body["payment_date"] == TODAY.isoformat()


def test_pay_bill_accepts_explicit_date(client):
    bill_id = make_bill(client).json()["id"]
    paid_on = (TODAY - timedelta(days=2)).isoformat()
    body = client.post(f"/api/bills/{bill_id}/pay", json={"payment_date": paid_on}).json()
    assert body["payment_date"] == paid_on


def test_unpay_undoes_a_payment(client):
    bill_id = make_bill(client).json()["id"]
    client.post(f"/api/bills/{bill_id}/pay", json={})
    body = client.post(f"/api/bills/{bill_id}/unpay", json={}).json()
    assert body["status"] == "unpaid"
    assert body["payment_date"] is None


def test_paying_a_recurring_bill_can_create_the_next_cycle(client):
    bill_id = make_bill(
        client, recurring=True, recurrence_interval="monthly",
        due_date=(TODAY + timedelta(days=3)).isoformat(),
    ).json()["id"]

    response = client.post(f"/api/bills/{bill_id}/pay", json={"mark_next_cycle": True})
    assert response.status_code == 200

    bills = client.get("/api/bills").json()
    assert bills["total"] == 2


def test_next_cycle_is_never_created_twice(client):
    """Paying the same recurring bill again must not duplicate the next cycle."""
    bill_id = make_bill(
        client, recurring=True, recurrence_interval="monthly",
        due_date=(TODAY + timedelta(days=3)).isoformat(),
    ).json()["id"]

    client.post(f"/api/bills/{bill_id}/pay", json={"mark_next_cycle": True})
    client.post(f"/api/bills/{bill_id}/pay", json={"mark_next_cycle": True})
    client.post(f"/api/bills/{bill_id}/pay", json={"mark_next_cycle": True})

    assert client.get("/api/bills").json()["total"] == 2


def test_next_cycle_due_date_is_returned(client):
    body = make_bill(client, recurring=True, recurrence_interval="monthly").json()
    assert body["next_cycle_due_date"] is not None
    assert body["recurrence_label"] == "Monthly"


def test_one_time_bill_has_no_next_cycle(client):
    body = make_bill(client, recurring=False, recurrence_interval="none").json()
    assert body["next_cycle_due_date"] is None


def test_one_time_bill_cannot_keep_a_recurrence_interval(client):
    """Creating a non-recurring bill forces the interval back to 'none'."""
    body = make_bill(client, recurring=False, recurrence_interval="monthly").json()
    assert body["recurrence_interval"] == "none"


# ------------------------------------------------------------------- overdue


def test_unpaid_bill_past_due_date_is_reported_overdue(client):
    make_bill(client, due_date=(TODAY - timedelta(days=4)).isoformat())
    body = client.get("/api/bills").json()["items"][0]
    assert body["status"] == "overdue"
    assert body["is_overdue"] is True
    assert body["days_until_due"] == -4


# ------------------------------------------------------------------- summary


def test_bill_summary_totals(client):
    make_bill(client, bill_name="A", amount="100", due_date=(TODAY + timedelta(days=2)).isoformat())
    make_bill(client, bill_name="B", amount="250.50", due_date=(TODAY + timedelta(days=4)).isoformat())
    make_bill(client, bill_name="C", amount="50", status="paid", due_date=TODAY.isoformat())

    summary = client.get("/api/bills/summary").json()
    assert summary["total_bills"] == 3
    assert summary["unpaid_count"] == 2
    assert summary["paid_count"] == 1
    assert summary["total_unpaid_amount"] == "350.50"
    assert summary["total_paid_this_month"] == "50.00"
    assert summary["next_due_bill_name"] == "A"
    assert summary["next_due_date"] == (TODAY + timedelta(days=2)).isoformat()


def test_bill_summary_is_empty_without_data(client):
    summary = client.get("/api/bills/summary").json()
    assert summary["total_bills"] == 0
    assert summary["total_unpaid_amount"] == "0.00"
    assert summary["next_due_date"] is None


def test_money_uses_decimal_not_float(client):
    """0.1 + 0.2 must equal exactly 0.30, which floats would get wrong."""
    make_bill(client, bill_name="A", amount="0.10")
    make_bill(client, bill_name="B", amount="0.20")
    summary = client.get("/api/bills/summary").json()
    assert summary["total_unpaid_amount"] == "0.30"


def test_due_soon_count(client):
    make_bill(client, bill_name="Soon", due_date=(TODAY + timedelta(days=3)).isoformat())
    make_bill(client, bill_name="Later", due_date=(TODAY + timedelta(days=20)).isoformat())
    summary = client.get("/api/bills/summary").json()
    assert summary["due_soon_count"] == 1