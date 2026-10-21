"""Tests for the dashboard aggregation, the reminder centre and settings."""

from datetime import date, datetime, timedelta, timezone

TODAY = date.today()


def seed_every_module(client) -> None:
    """Create at least one real record in each of the four modules."""
    client.post("/api/bills", json={
        "bill_name": "Electricity Bill",
        "category": "electricity",
        "amount": "1250.00",
        "currency": "INR",
        "due_date": (TODAY + timedelta(days=3)).isoformat(),
    })
    client.post("/api/documents", json={
        "document_name": "Vehicle Insurance",
        "document_type": "vehicle_insurance",
        "expiry_date": (TODAY + timedelta(days=12)).isoformat(),
        "reminder_days_before": 30,
    })
    client.post("/api/medications", json={
        "medication_name": "Vitamin D3 (test)",
        "dosage": "1",
        "dosage_unit": "tablet",
        "start_date": TODAY.isoformat(),
        # 00:05 is reliably inside the reminder window whenever the tests run.
        "scheduled_times": ["00:05"],
    })
    client.post("/api/hydration/intake", json={"amount_ml": 750})


# ------------------------------------------------------------------ dashboard


def test_dashboard_summary_with_empty_database(client):
    body = client.get("/api/dashboard/summary").json()
    assert body["bills"]["total_bills"] == 0
    assert body["documents"]["total_documents"] == 0
    assert body["medications"]["active_schedules"] == 0
    assert body["hydration"]["consumed_today_ml"] == 0
    assert body["greeting_name"].endswith("!")


def test_dashboard_summary_reflects_real_data(client):
    seed_every_module(client)
    body = client.get("/api/dashboard/summary").json()

    assert body["bills"]["total_bills"] == 1
    assert body["bills"]["total_unpaid_amount"] == "1250.00"
    assert body["bills"]["next_due_bill_name"] == "Electricity Bill"

    assert body["documents"]["total_documents"] == 1
    assert body["documents"]["next_expiry_name"] == "Vehicle Insurance"

    assert body["medications"]["active_schedules"] == 1
    assert body["medications"]["doses_today_total"] == 1

    assert body["hydration"]["consumed_today_ml"] == 750
    assert body["hydration"]["daily_goal_ml"] == 2000
    assert body["hydration"]["percent_complete"] == 38


def test_dashboard_does_not_use_hardcoded_numbers(client):
    """The same endpoint must return different numbers when the data changes."""
    seed_every_module(client)
    first = client.get("/api/dashboard/summary").json()

    client.post("/api/hydration/intake", json={"amount_ml": 1250})
    second = client.get("/api/dashboard/summary").json()

    assert second["hydration"]["consumed_today_ml"] == 2000
    assert second["hydration"]["consumed_today_ml"] != first["hydration"]["consumed_today_ml"]


def test_dashboard_charts_shape(client):
    seed_every_module(client)
    body = client.get("/api/dashboard/charts").json()

    assert len(body["hydration_weekly"]) == 7
    assert len(body["medication_weekly"]) == 7
    assert set(body["bills_paid_vs_unpaid"].keys()) == {"paid", "unpaid"}
    assert body["document_expiry_buckets"]["in_7_days"] == 0
    assert body["document_expiry_buckets"]["in_30_days"] == 1


def test_dashboard_charts_empty_database(client):
    body = client.get("/api/dashboard/charts").json()
    assert len(body["hydration_weekly"]) == 7
    assert body["bills_paid_vs_unpaid"] == {"paid": 0.0, "unpaid": 0.0}
    assert body["bills_by_category"] == []


def test_dashboard_activity_is_built_from_real_rows(client):
    seed_every_module(client)
    body = client.get("/api/dashboard/activity").json()

    assert body["total"] > 0
    modules = {item["module"] for item in body["items"]}
    assert "billbell" in modules
    assert "dateguard" in modules
    assert "aquahabit" in modules
    assert all(item["link"] for item in body["items"])


def test_dashboard_activity_is_sorted_newest_first(client):
    seed_every_module(client)
    body = client.get("/api/dashboard/activity").json()
    timestamps = [item["occurred_at"] for item in body["items"]]
    assert timestamps == sorted(timestamps, reverse=True)


# ------------------------------------------------------------------ reminders


def test_reminders_empty_database(client):
    body = client.get("/api/reminders").json()
    assert body["total"] == 0
    assert body["items"] == []


def test_reminders_combine_all_modules(client):
    seed_every_module(client)
    body = client.get("/api/reminders").json()
    modules = {item["module"] for item in body["items"]}
    assert "billbell" in modules
    assert "dateguard" in modules
    assert "dosenote" in modules


def test_reminders_have_no_duplicate_ids(client):
    """The same real-world event must never be listed twice."""
    seed_every_module(client)
    body = client.get("/api/reminders").json()
    ids = [item["id"] for item in body["items"]]
    assert len(ids) == len(set(ids))


def test_reminders_are_sorted_by_due_date(client):
    client.post("/api/bills", json={
        "bill_name": "Due tomorrow", "amount": "100",
        "due_date": (TODAY + timedelta(days=1)).isoformat(),
    })
    client.post("/api/bills", json={
        "bill_name": "Overdue", "amount": "100",
        "due_date": (TODAY - timedelta(days=5)).isoformat(),
    })
    body = client.get("/api/reminders").json()
    due_times = [item["due_at"] for item in body["items"]]
    assert due_times == sorted(due_times)


def test_reminders_grouped_into_buckets(client):
    client.post("/api/bills", json={
        "bill_name": "Overdue bill", "amount": "100",
        "due_date": (TODAY - timedelta(days=3)).isoformat(),
    })
    client.post("/api/bills", json={
        "bill_name": "Today bill", "amount": "100",
        "due_date": TODAY.isoformat(),
    })
    client.post("/api/bills", json={
        "bill_name": "Future bill", "amount": "100",
        "due_date": (TODAY + timedelta(days=2)).isoformat(),
    })
    body = client.get("/api/reminders").json()

    assert len(body["groups"]["overdue"]) == 1
    assert len(body["groups"]["today"]) == 1
    assert len(body["groups"]["upcoming"]) == 1
    assert body["overdue_count"] == 1
    assert body["today_count"] == 1
    assert body["upcoming_count"] == 1


def test_reminders_can_be_filtered_by_module(client):
    seed_every_module(client)
    body = client.get("/api/reminders", params={"module": ["billbell"]}).json()
    assert all(item["module"] == "billbell" for item in body["items"])


def test_reminders_can_be_filtered_by_priority(client):
    client.post("/api/bills", json={
        "bill_name": "Very overdue", "amount": "100",
        "due_date": (TODAY - timedelta(days=20)).isoformat(),
    })
    body = client.get("/api/reminders", params={"priority": ["urgent"]}).json()
    assert all(item["priority"] == "urgent" for item in body["items"])


def test_reminder_links_point_at_real_routes(client):
    client.post("/api/bills", json={
        "bill_name": "Linked bill", "amount": "100",
        "due_date": (TODAY + timedelta(days=1)).isoformat(),
    })
    body = client.get("/api/reminders").json()
    item = next(i for i in body["items"] if i["module"] == "billbell")
    assert item["link"].startswith("/bills?bill=")


def test_reminder_summary_matches_the_list(client):
    seed_every_module(client)
    summary = client.get("/api/reminders/summary").json()
    listed = client.get("/api/reminders").json()
    assert summary["total"] == listed["total"]


def test_paying_a_bill_removes_its_overdue_reminder(client):
    """Reminders are derived, so paying a bill must clear its reminder."""
    created = client.post("/api/bills", json={
        "bill_name": "To be paid", "amount": "100",
        "due_date": (TODAY - timedelta(days=2)).isoformat(),
    }).json()

    before = client.get("/api/reminders").json()["total"]
    assert before > 0

    client.post(f"/api/bills/{created['id']}/pay", json={})
    after = client.get("/api/reminders").json()["total"]
    assert after < before


def test_taken_dose_is_no_longer_reminded(client):
    client.post("/api/medications", json={
        "medication_name": "Dose test",
        "dosage": "1",
        "start_date": TODAY.isoformat(),
        "scheduled_times": ["00:05"],
    })
    before = client.get("/api/reminders", params={"module": ["dosenote"]}).json()["total"]
    assert before >= 1

    today = client.get("/api/medications/today").json()
    client.patch(f"/api/doses/{today['doses'][0]['id']}", json={"status": "taken"})

    after = client.get("/api/reminders", params={"module": ["dosenote"]}).json()["total"]
    assert after == before - 1


def test_upcoming_reminders_endpoint(client):
    seed_every_module(client)
    body = client.get("/api/reminders/upcoming", params={"days": 30}).json()
    assert isinstance(body, list)
    assert all(item["due_date"] <= (TODAY + timedelta(days=30)).isoformat() for item in body)


# ------------------------------------------------------------------- settings


def test_settings_defaults(client):
    body = client.get("/api/settings").json()
    assert body["default_currency"] == "INR"
    assert body["theme"] == "light"
    assert body["bill_reminder_days_before"] == 3
    assert body["notes"]["default_currency"]


def test_update_theme(client):
    body = client.patch("/api/settings", json={"theme": "dark"}).json()
    assert body["theme"] == "dark"


def test_reject_invalid_theme(client):
    assert client.patch("/api/settings", json={"theme": "neon"}).status_code == 422


def test_reject_unsupported_currency(client):
    assert client.patch("/api/settings", json={"default_currency": "XYZ"}).status_code == 422


def test_partial_settings_update_keeps_other_fields(client):
    client.patch("/api/settings", json={"theme": "dark"})
    body = client.patch("/api/settings", json={"bill_reminder_days_before": 5}).json()
    assert body["theme"] == "dark"  # unchanged
    assert body["bill_reminder_days_before"] == 5


def test_settings_persist_across_requests(client):
    client.patch("/api/settings", json={"bill_reminder_days_before": 7})
    assert client.get("/api/settings").json()["bill_reminder_days_before"] == 7


def test_bill_reminder_window_affects_reminders(client):
    """No reminder for a bill due in 5 days with a 1-day window."""
    client.post("/api/bills", json={
        "bill_name": "Not yet urgent", "amount": "100",
        "due_date": (TODAY + timedelta(days=5)).isoformat(),
    })
    assert client.get("/api/reminders", params={"module": ["billbell"]}).json()["total"] == 0

    client.patch("/api/settings", json={"bill_reminder_days_before": 7})
    assert client.get("/api/reminders", params={"module": ["billbell"]}).json()["total"] == 1


def test_settings_meta_lists_options(client):
    body = client.get("/api/settings/meta").json()
    assert "INR" in body["currencies"]
    assert body["themes"] == ["light", "dark"]
    assert body["hydration_quick_add_ml"] == [150, 250, 350, 500]


def test_health_endpoint(client):
    body = client.get("/api/health").json()
    assert body["status"] == "ok"
    assert body["database_connected"] is True
    assert body["modules"] == ["BillBell", "DateGuard", "DoseNote", "AquaHabit"]


def test_root_index_lists_modules(client):
    body = client.get("/").json()
    assert body["app"] == "DailyFlow API"
    assert "billbell" in body["modules"]


def test_unknown_route_returns_json_error_not_a_stack_trace(client):
    response = client.get("/api/does-not-exist")
    assert response.status_code == 404
    body = response.json()
    assert body["success"] is False
    assert "Traceback" not in response.text