"""Tests for DateGuard: documents, derived expiry status and renewals."""

from datetime import date, timedelta

TODAY = date.today()


def make_document(client, **overrides):
    payload = {
        "document_name": "Driving Licence",
        "document_type": "driving_licence",
        "expiry_date": (TODAY + timedelta(days=45)).isoformat(),
        "reminder_days_before": 30,
    }
    payload.update(overrides)
    return client.post("/api/documents", json=payload)


# --------------------------------------------------------------------- create


def test_create_document_returns_201(client):
    response = make_document(client)
    assert response.status_code == 201
    body = response.json()
    assert body["document_name"] == "Driving Licence"
    assert body["status"] == "valid"
    assert body["days_remaining"] == 45


def test_create_document_rejects_unknown_type(client):
    assert make_document(client, document_type="spaceship").status_code == 422


def test_create_document_rejects_absurd_reminder_window(client):
    assert make_document(client, reminder_days_before=9999).status_code == 422


def test_create_document_rejects_missing_expiry(client):
    response = client.post("/api/documents", json={"document_name": "No Date"})
    assert response.status_code == 422


def test_document_number_is_masked_in_lists(client):
    make_document(client, document_number="DL-1234-9876543")
    listed = client.get("/api/documents").json()["items"][0]
    assert listed["document_number"] is None
    assert listed["masked_document_number"].endswith("6543")


def test_single_document_returns_the_real_number(client):
    make_document(client, document_number="DL-1234-9876543")
    doc_id = client.get("/api/documents").json()["items"][0]["id"]
    single = client.get(f"/api/documents/{doc_id}").json()
    assert single["document_number"] == "DL-1234-9876543"


# ------------------------------------------------------ derived expiry status


def test_status_valid_when_far_from_expiry(client):
    body = make_document(client, expiry_date=(TODAY + timedelta(days=200)).isoformat()).json()
    assert body["status"] == "valid"
    assert body["is_expired"] is False


def test_status_expiring_soon_inside_reminder_window(client):
    body = make_document(
        client, expiry_date=(TODAY + timedelta(days=10)).isoformat(), reminder_days_before=30
    ).json()
    assert body["status"] == "expiring_soon"
    assert body["is_expiring_soon"] is True


def test_status_outside_reminder_window_is_valid(client):
    body = make_document(
        client, expiry_date=(TODAY + timedelta(days=10)).isoformat(), reminder_days_before=5
    ).json()
    assert body["status"] == "valid"


def test_status_expired_yesterday(client):
    body = make_document(client, expiry_date=(TODAY - timedelta(days=1)).isoformat()).json()
    assert body["status"] == "expired"
    assert body["is_expired"] is True
    assert body["days_remaining"] == -1


def test_status_expires_today_is_expiring_not_expired(client):
    """A document expiring today has zero days left, but is not yet expired."""
    body = make_document(client, expiry_date=TODAY.isoformat(), reminder_days_before=30).json()
    assert body["days_remaining"] == 0
    assert body["status"] == "expiring_soon"
    assert body["is_expired"] is False


def test_expiry_status_is_derived_not_stored(client, db):
    """Editing the expiry date immediately changes the derived status."""
    doc_id = make_document(client, expiry_date=(TODAY + timedelta(days=300)).isoformat()).json()["id"]
    assert client.get(f"/api/documents/{doc_id}").json()["status"] == "valid"

    client.patch(
        f"/api/documents/{doc_id}", json={"expiry_date": (TODAY - timedelta(days=2)).isoformat()}
    )
    assert client.get(f"/api/documents/{doc_id}").json()["status"] == "expired"


def test_leap_day_expiry_calculates_correctly(client):
    """A document expiring 29 Feb 2028 (a real leap day) must work."""
    doc_id = make_document(client, expiry_date="2028-02-29").json()["id"]
    body = client.get(f"/api/documents/{doc_id}").json()
    assert body["expiry_date"] == "2028-02-29"
    # JSON carries dates as ISO strings, so parse before doing date maths.
    assert (date.fromisoformat(body["expiry_date"]) - TODAY).days == body["days_remaining"]


# -------------------------------------------------------- list, filter, sort


def test_filter_documents_by_expiry_status(client):
    make_document(client, document_name="Valid", expiry_date=(TODAY + timedelta(days=300)).isoformat())
    make_document(client, document_name="Soon", expiry_date=(TODAY + timedelta(days=5)).isoformat())
    make_document(client, document_name="Gone", expiry_date=(TODAY - timedelta(days=5)).isoformat())

    assert client.get("/api/documents", params={"status": "expired"}).json()["total"] == 1
    assert client.get("/api/documents", params={"status": "expiring_soon"}).json()["total"] == 1
    assert client.get("/api/documents", params={"status": "valid"}).json()["total"] == 1


def test_filter_documents_by_type(client):
    make_document(client, document_type="passport")
    make_document(client, document_type="vehicle_insurance")
    result = client.get("/api/documents", params={"document_type": "passport"}).json()
    assert result["total"] == 1
    assert result["items"][0]["document_type_label"] == "Passport"


def test_search_documents(client):
    make_document(client, document_name="Passport")
    make_document(client, document_name="Aadhaar", document_type="aadhaar")
    result = client.get("/api/documents", params={"search": "Passport"}).json()
    assert result["total"] == 1


def test_sort_documents_by_expiry(client):
    make_document(client, document_name="C", expiry_date=(TODAY + timedelta(days=30)).isoformat())
    make_document(client, document_name="A", expiry_date=(TODAY + timedelta(days=1)).isoformat())
    make_document(client, document_name="B", expiry_date=(TODAY + timedelta(days=10)).isoformat())

    items = client.get("/api/documents", params={"sort_by": "expiry_date", "sort_order": "asc"}).json()["items"]
    assert [d["document_name"] for d in items] == ["A", "B", "C"]


def test_expiring_endpoint_respects_window(client):
    make_document(client, document_name="Soon", expiry_date=(TODAY + timedelta(days=5)).isoformat())
    make_document(client, document_name="Later", expiry_date=(TODAY + timedelta(days=100)).isoformat())

    within_30 = client.get("/api/documents/expiring", params={"within_days": 30}).json()
    assert [d["document_name"] for d in within_30] == ["Soon"]

    within_120 = client.get("/api/documents/expiring", params={"within_days": 120}).json()
    assert len(within_120) == 2


# ------------------------------------------------------------------ renewals


def test_renew_updates_expiry_and_keeps_history(client):
    doc_id = make_document(client, expiry_date=(TODAY + timedelta(days=10)).isoformat()).json()["id"]
    original_expiry = (TODAY + timedelta(days=10)).isoformat()

    response = client.post(
        f"/api/documents/{doc_id}/renew",
        json={"new_expiry_date": (TODAY + timedelta(days=400)).isoformat(), "notes": "Renewed at office"},
    )
    assert response.status_code == 200
    body = response.json()

    assert body["expiry_date"] == (TODAY + timedelta(days=400)).isoformat()
    assert body["status"] == "valid"
    assert len(body["renewals"]) == 1
    assert body["renewals"][0]["previous_expiry_date"] == original_expiry


def test_renew_rejects_a_backwards_date(client):
    doc_id = make_document(client).json()["id"]
    response = client.post(
        f"/api/documents/{doc_id}/renew",
        json={"new_expiry_date": (TODAY - timedelta(days=30)).isoformat()},
    )
    assert response.status_code == 400


def test_renewal_history_accumulates(client):
    doc_id = make_document(client).json()["id"]
    client.post(f"/api/documents/{doc_id}/renew", json={"new_expiry_date": (TODAY + timedelta(days=400)).isoformat()})
    body = client.post(
        f"/api/documents/{doc_id}/renew", json={"new_expiry_date": (TODAY + timedelta(days=800)).isoformat()}
    ).json()
    assert len(body["renewals"]) == 2


# ------------------------------------------------------------------ summary


def test_document_summary_counts_windows(client):
    make_document(client, document_name="Expired", expiry_date=(TODAY - timedelta(days=2)).isoformat())
    make_document(client, document_name="Day7", expiry_date=(TODAY + timedelta(days=7)).isoformat())
    make_document(client, document_name="Day20", expiry_date=(TODAY + timedelta(days=20)).isoformat())
    make_document(client, document_name="Far", expiry_date=(TODAY + timedelta(days=300)).isoformat())

    summary = client.get("/api/documents/summary").json()
    assert summary["total_documents"] == 4
    assert summary["expired_count"] == 1
    # +7 days is inside 7, 15 and 30. +20 is only inside 30.
    assert summary["expiring_in_7_days"] == 1
    assert summary["expiring_in_15_days"] == 1
    assert summary["expiring_in_30_days"] == 2
    assert summary["next_expiry_name"] == "Day7"


def test_document_summary_empty(client):
    summary = client.get("/api/documents/summary").json()
    assert summary["total_documents"] == 0
    assert summary["next_expiry_date"] is None


def test_delete_document(client):
    doc_id = make_document(client).json()["id"]
    assert client.delete(f"/api/documents/{doc_id}").status_code == 200
    assert client.get(f"/api/documents/{doc_id}").status_code == 404


def test_missing_document_returns_404(client):
    assert client.get("/api/documents/987654").status_code == 404