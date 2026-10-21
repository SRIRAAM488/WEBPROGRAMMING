"""Tests for DoseNote: schedules, dose logs, duplicates and adherence."""

from datetime import date, timedelta

TODAY = date.today()


def make_schedule(client, **overrides):
    payload = {
        "medication_name": "Vitamin D3 (test)",
        "dosage": "1",
        "dosage_unit": "tablet",
        "start_date": TODAY.isoformat(),
        "scheduled_times": ["08:00"],
    }
    payload.update(overrides)
    return client.post("/api/medications", json=payload)


# ------------------------------------------------------------------ schedules


def test_create_schedule_returns_201(client):
    response = make_schedule(client)
    assert response.status_code == 201
    body = response.json()
    assert body["medication_name"] == "Vitamin D3 (test)"
    assert body["scheduled_times"] == ["08:00:00"]
    assert body["time_labels"] == ["8:00 AM"]


def test_schedule_times_are_deduplicated_and_sorted(client):
    body = make_schedule(client, scheduled_times=["20:00", "08:00", "20:00"]).json()
    assert body["scheduled_times"] == ["08:00:00", "20:00:00"]


def test_schedule_rejects_empty_times(client):
    assert make_schedule(client, scheduled_times=[]).status_code == 422


def test_schedule_rejects_invalid_time(client):
    assert make_schedule(client, scheduled_times=["25:00"]).status_code == 422


def test_schedule_rejects_too_many_times(client):
    times = [f"{h:02d}:00" for h in range(13)]
    assert make_schedule(client, scheduled_times=times).status_code == 422


def test_schedule_rejects_end_before_start(client):
    response = make_schedule(
        client,
        start_date=TODAY.isoformat(),
        end_date=(TODAY - timedelta(days=5)).isoformat(),
    )
    assert response.status_code == 422


def test_schedule_rejects_unknown_unit(client):
    assert make_schedule(client, dosage_unit="furlongs").status_code == 422


def test_patch_schedule_changes_times(client):
    schedule_id = make_schedule(client).json()["id"]
    body = client.patch(
        f"/api/medications/{schedule_id}", json={"scheduled_times": ["07:00", "19:00"]}
    ).json()
    assert body["scheduled_times"] == ["07:00:00", "19:00:00"]


def test_deactivate_schedule(client):
    """Deactivating keeps the record (and its dose logs) instead of deleting."""
    schedule_id = make_schedule(client).json()["id"]
    body = client.patch(f"/api/medications/{schedule_id}", json={"active": False}).json()
    assert body["active"] is False
    assert body["is_active_today"] is False


def test_inactive_schedule_produces_no_doses(client):
    make_schedule(client, active=False)
    today = client.get("/api/medications/today").json()
    assert today["total_doses"] == 0


def test_schedule_end_date_stops_doses(client):
    make_schedule(client, end_date=(TODAY - timedelta(days=1)).isoformat())
    today = client.get("/api/medications/today").json()
    assert today["total_doses"] == 0


def test_delete_schedule_removes_dose_logs(client):
    schedule_id = make_schedule(client).json()["id"]
    client.post(f"/api/medications/{schedule_id}/doses", json={"scheduled_time": "08:00"})
    assert client.delete(f"/api/medications/{schedule_id}").status_code == 200
    assert client.get("/api/medications").json() == []


def test_missing_schedule_returns_404(client):
    assert client.get("/api/medications/999999").status_code == 404


def test_today_route_is_not_treated_as_an_id(client):
    """/medications/today must be matched as a fixed route."""
    assert client.get("/api/medications/today").status_code == 200


# ------------------------------------------------------------------ dose logs


def test_dose_logs_are_generated_as_pending(client):
    make_schedule(client)
    today = client.get("/api/medications/today").json()
    assert today["total_doses"] == 1
    assert today["pending"] == 1
    assert today["doses"][0]["status"] == "pending"
    assert today["doses"][0]["taken_at"] is None


def test_generation_is_idempotent(client):
    """Calling today's endpoint twice must not create duplicate dose logs."""
    make_schedule(client)
    client.get("/api/medications/today")
    client.get("/api/medications/today")
    client.get("/api/medications/today")
    assert client.get("/api/medications/today").json()["total_doses"] == 1


def test_duplicate_dose_log_is_rejected(client):
    """The core duplicate-prevention rule for DoseNote."""
    schedule_id = make_schedule(client).json()["id"]
    first = client.post(f"/api/medications/{schedule_id}/doses", json={"scheduled_time": "08:00"})
    assert first.status_code == 201

    second = client.post(f"/api/medications/{schedule_id}/doses", json={"scheduled_time": "08:00"})
    assert second.status_code == 409
    assert "already exists" in second.json()["detail"]


def test_dose_time_must_belong_to_the_schedule(client):
    schedule_id = make_schedule(client, scheduled_times=["08:00", "20:00"]).json()["id"]
    response = client.post(f"/api/medications/{schedule_id}/doses", json={"scheduled_time": "13:00"})
    assert response.status_code == 400


def test_mark_dose_taken_records_timestamp(client):
    schedule_id = make_schedule(client).json()["id"]
    dose_id = client.post(
        f"/api/medications/{schedule_id}/doses", json={"scheduled_time": "08:00"}
    ).json()["id"]

    body = client.patch(f"/api/doses/{dose_id}", json={"status": "taken"}).json()
    assert body["status"] == "taken"
    assert body["taken_at"] is not None


def test_dose_can_be_marked_skipped(client):
    schedule_id = make_schedule(client).json()["id"]
    dose_id = client.post(
        f"/api/medications/{schedule_id}/doses", json={"scheduled_time": "08:00"}
    ).json()["id"]

    body = client.patch(f"/api/doses/{dose_id}", json={"status": "skipped"}).json()
    assert body["status"] == "skipped"
    assert body["taken_at"] is None


def test_dose_can_be_corrected_back_to_pending(client):
    """A mis-click must be reversible, and taken_at must be cleared."""
    schedule_id = make_schedule(client).json()["id"]
    dose_id = client.post(
        f"/api/medications/{schedule_id}/doses", json={"scheduled_time": "08:00"}
    ).json()["id"]

    client.patch(f"/api/doses/{dose_id}", json={"status": "taken"})
    body = client.patch(f"/api/doses/{dose_id}", json={"status": "pending"}).json()
    assert body["status"] == "pending"
    assert body["taken_at"] is None


def test_delete_dose_log(client):
    schedule_id = make_schedule(client).json()["id"]
    dose_id = client.post(
        f"/api/medications/{schedule_id}/doses", json={"scheduled_time": "08:00"}
    ).json()["id"]
    assert client.delete(f"/api/doses/{dose_id}").status_code == 200
    assert client.patch(f"/api/doses/{dose_id}", json={"status": "taken"}).status_code == 404


def test_today_completion_percentage(client):
    make_schedule(client, scheduled_times=["01:00", "02:00", "03:00"])
    today = client.get("/api/medications/today").json()
    assert today["total_doses"] == 3

    for dose in today["doses"][:2]:
        client.patch(f"/api/doses/{dose['id']}", json={"status": "taken"})

    updated = client.get("/api/medications/today").json()
    assert updated["taken"] == 2
    assert updated["completion_percent"] == 67


# ----------------------------------------------------------------- adherence


def test_adherence_returns_one_point_per_day(client):
    make_schedule(client)
    body = client.get("/api/medications/adherence", params={"days": 7}).json()
    assert len(body["daily"]) == 7
    assert body["start_date"] == (TODAY - timedelta(days=6)).isoformat()
    assert body["end_date"] == TODAY.isoformat()


def test_adherence_percentage_counts_taken_doses(client):
    make_schedule(client, scheduled_times=["01:00", "02:00"])
    today = client.get("/api/medications/today").json()
    client.patch(f"/api/doses/{today['doses'][0]['id']}", json={"status": "taken"})

    body = client.get("/api/medications/adherence", params={"days": 1}).json()
    assert body["total_scheduled"] == 2
    assert body["total_taken"] == 1
    assert body["overall_adherence_percent"] == 50


def test_adherence_with_no_schedules_is_zero_not_an_error(client):
    body = client.get("/api/medications/adherence", params={"days": 7}).json()
    assert body["overall_adherence_percent"] == 0
    assert len(body["daily"]) == 7


def test_history_returns_daily_and_recent(client):
    make_schedule(client)
    body = client.get("/api/medications/history").json()
    assert len(body["daily"]) == 7
    assert isinstance(body["recent"], list)


def test_today_is_empty_without_schedules(client):
    body = client.get("/api/medications/today").json()
    assert body["total_doses"] == 0
    assert body["completion_percent"] == 0