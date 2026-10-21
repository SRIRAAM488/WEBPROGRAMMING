"""Tests for AquaHabit: intake records, goals and daily/weekly rollups."""

from datetime import date, datetime, timedelta, timezone

TODAY = date.today()


def add_water(client, amount, **overrides):
    payload = {"amount_ml": amount}
    payload.update(overrides)
    return client.post("/api/hydration/intake", json=payload)


# --------------------------------------------------------------------- intake


def test_add_intake_returns_201(client):
    response = add_water(client, 250)
    assert response.status_code == 201
    body = response.json()
    assert body["amount_ml"] == 250
    assert body["entry_date"] == TODAY.isoformat()


def test_zero_amount_is_rejected(client):
    assert add_water(client, 0).status_code == 422


def test_negative_amount_is_rejected(client):
    assert add_water(client, -100).status_code == 422


def test_absurd_amount_is_rejected(client):
    assert add_water(client, 999999).status_code == 422


def test_missing_amount_is_rejected(client):
    assert client.post("/api/hydration/intake", json={}).status_code == 422


def test_update_intake_amount(client):
    entry_id = add_water(client, 250).json()["id"]
    body = client.patch(f"/api/hydration/intake/{entry_id}", json={"amount_ml": 400}).json()
    assert body["amount_ml"] == 400


def test_update_intake_rejects_negative(client):
    entry_id = add_water(client, 250).json()["id"]
    assert client.patch(f"/api/hydration/intake/{entry_id}", json={"amount_ml": -5}).status_code == 422


def test_delete_intake(client):
    entry_id = add_water(client, 250).json()["id"]
    assert client.delete(f"/api/hydration/intake/{entry_id}").status_code == 200
    assert client.get("/api/hydration/today").json()["total_ml"] == 0


def test_missing_intake_returns_404(client):
    assert client.delete("/api/hydration/intake/999999").status_code == 404
    assert client.patch("/api/hydration/intake/999999", json={"amount_ml": 100}).status_code == 404


def test_intake_can_be_backdated(client):
    """Logging a glass for yesterday must file it under yesterday."""
    yesterday = TODAY - timedelta(days=1)
    consumed = datetime.combine(yesterday, datetime.min.time(), tzinfo=timezone.utc)
    add_water(client, 300, consumed_at=consumed.isoformat())

    assert client.get("/api/hydration/today").json()["total_ml"] == 0

    week = client.get("/api/hydration/weekly").json()
    yesterday_point = next(d for d in week["daily"] if d["date"] == yesterday.isoformat())
    assert yesterday_point["total_ml"] == 300


# --------------------------------------------------------------------- goals


def test_default_settings(client):
    body = client.get("/api/hydration/settings").json()
    assert body["daily_goal_ml"] == 2000
    assert body["default_serving_ml"] == 250
    assert "not medical advice" in body["note"]


def test_update_goal(client):
    body = client.patch("/api/hydration/settings", json={"daily_goal_ml": 2500}).json()
    assert body["daily_goal_ml"] == 2500


def test_update_serving_size(client):
    body = client.patch("/api/hydration/settings", json={"default_serving_ml": 350}).json()
    assert body["default_serving_ml"] == 350


def test_goal_must_be_positive(client):
    assert client.patch("/api/hydration/settings", json={"daily_goal_ml": 0}).status_code == 422
    assert client.patch("/api/hydration/settings", json={"daily_goal_ml": -500}).status_code == 422


def test_changing_the_goal_does_not_delete_history(client):
    add_water(client, 500)
    client.patch("/api/hydration/settings", json={"daily_goal_ml": 1000})

    today = client.get("/api/hydration/today").json()
    assert today["total_ml"] == 500  # intake untouched
    assert today["goal_ml"] == 1000  # goal recalculated
    assert today["percent_complete"] == 50


# ---------------------------------------------------------------- today view


def test_today_totals_and_percentage(client):
    add_water(client, 250)
    add_water(client, 350)
    body = client.get("/api/hydration/today").json()

    assert body["total_ml"] == 600
    assert body["goal_ml"] == 2000
    assert body["remaining_ml"] == 1400
    assert body["percent_complete"] == 30
    assert body["goal_reached"] is False
    assert len(body["entries"]) == 2


def test_goal_reached_is_flagged(client):
    add_water(client, 2000)
    body = client.get("/api/hydration/today").json()
    assert body["goal_reached"] is True
    assert body["percent_complete"] == 100
    assert body["remaining_ml"] == 0


def test_goal_can_be_exceeded_without_capping(client):
    """Over-drinking must show the real total, not a capped 2000."""
    add_water(client, 2000)
    add_water(client, 750)
    body = client.get("/api/hydration/today").json()
    assert body["total_ml"] == 2750
    assert body["percent_complete"] == 138


def test_today_is_empty_by_default(client):
    body = client.get("/api/hydration/today").json()
    assert body["total_ml"] == 0
    assert body["percent_complete"] == 0
    assert body["entries"] == []


def test_daily_progress_resets_without_deleting_history(client):
    """Yesterday's entries must not appear in today's total, and must survive."""
    yesterday = TODAY - timedelta(days=1)
    add_water(client, 900, entry_date=yesterday.isoformat())
    add_water(client, 100)

    today = client.get("/api/hydration/today").json()
    assert today["total_ml"] == 100  # only today's entry counts

    week = client.get("/api/hydration/weekly").json()
    yesterday_point = next(d for d in week["daily"] if d["date"] == yesterday.isoformat())
    assert yesterday_point["total_ml"] == 900  # history preserved


# ------------------------------------------------------------ weekly history


def test_weekly_returns_seven_days(client):
    body = client.get("/api/hydration/weekly", params={"days": 7}).json()
    assert len(body["daily"]) == 7
    assert body["daily"][-1]["date"] == TODAY.isoformat()
    assert body["daily"][0]["date"] == (TODAY - timedelta(days=6)).isoformat()


def test_weekly_zero_fills_missing_days(client):
    """A day with no entries must still appear, with 0 ml - otherwise charts break."""
    body = client.get("/api/hydration/weekly", params={"days": 7}).json()
    assert all(day["total_ml"] == 0 for day in body["daily"])
    assert all(day["entry_count"] == 0 for day in body["daily"])


def test_weekly_average_and_best_day(client):
    add_water(client, 1000)
    yesterday = TODAY - timedelta(days=1)
    add_water(client, 400, entry_date=yesterday.isoformat())

    body = client.get("/api/hydration/weekly", params={"days": 7}).json()
    assert body["total_ml"] == 1400
    assert body["average_ml"] == 200  # 1400 / 7 days
    assert body["best_day"]["total_ml"] == 1000


def test_weekly_counts_days_goal_reached(client):
    add_water(client, 2000)
    body = client.get("/api/hydration/weekly", params={"days": 7}).json()
    assert body["days_goal_reached"] == 1


def test_weekly_handles_a_changed_goal(client):
    add_water(client, 1000)
    client.patch("/api/hydration/settings", json={"daily_goal_ml": 800})
    body = client.get("/api/hydration/weekly", params={"days": 7}).json()
    assert body["goal_ml"] == 800
    assert body["days_goal_reached"] == 1


def test_history_range(client):
    add_water(client, 100)
    body = client.get(
        "/api/hydration/history",
        params={"start_date": (TODAY - timedelta(days=3)).isoformat(), "end_date": TODAY.isoformat()},
    ).json()
    assert len(body["daily"]) == 4
    assert body["total_ml"] == 100
    assert body["days_logged"] == 1


def test_monthly_summary(client):
    add_water(client, 500)
    body = client.get("/api/hydration/monthly").json()
    assert body["month"] == TODAY.strftime("%B")
    assert body["year"] == TODAY.year
    assert body["total_ml"] == 500
    assert body["days_logged"] == 1


def test_database_refuses_a_zero_goal(client, db):
    """A zero goal is rejected by a CHECK constraint, so no division by zero
    can ever reach the service layer."""
    import pytest
    from sqlalchemy.exc import IntegrityError

    from app.models.hydration import HydrationSettings

    row = db.get(HydrationSettings, 1)
    row.daily_goal_ml = 0
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_goal_changes_are_bounded(client):
    assert client.patch("/api/hydration/settings", json={"daily_goal_ml": 99999}).status_code == 422
    assert client.patch("/api/hydration/settings", json={"default_serving_ml": 0}).status_code == 422