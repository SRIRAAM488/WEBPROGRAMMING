"""Quick end-to-end check of every DailyFlow API group.

Usage (backend folder, venv active):
    python -m scripts.smoke_test [base_url]

This is a manual sanity script. The real automated tests live in backend/tests
and are run with pytest.
"""

import sys
from datetime import date, timedelta

import httpx

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8010"

passed = 0
failed: list[str] = []


def check(label: str, condition: bool, extra: str = "") -> None:
    global passed
    if condition:
        passed += 1
        print(f"  PASS  {label}")
    else:
        failed.append(label)
        print(f"  FAIL  {label} {extra}")


def main() -> int:
    today = date.today()
    client = httpx.Client(base_url=BASE, timeout=30.0)

    print("\n== General ==")
    r = client.get("/api/health")
    check("health returns ok", r.status_code == 200 and r.json()["status"] == "ok")
    check("swagger docs available", client.get("/docs").status_code == 200)

    print("\n== Dashboard ==")
    r = client.get("/api/dashboard/summary")
    check("summary 200", r.status_code == 200, r.text[:200])
    if r.status_code == 200:
        d = r.json()
        check("has all four modules", all(k in d for k in ("bills", "documents", "medications", "hydration")))
        check("bills total from DB", d["bills"]["total_bills"] > 0, str(d["bills"]))
        check("documents total from DB", d["documents"]["total_documents"] > 0)
        check("hydration goal set", d["hydration"]["daily_goal_ml"] > 0)
        check("medication schedules counted", d["medications"]["total_schedules"] > 0)

    r = client.get("/api/dashboard/charts")
    check("charts 200", r.status_code == 200, r.text[:200])
    if r.status_code == 200:
        c = r.json()
        check("weekly hydration has 7 points", len(c["hydration_weekly"]) == 7)
        check("hydration points carry data", any(p["total_ml"] > 0 for p in c["hydration_weekly"]))
        check("paid vs unpaid computed", set(c["bills_paid_vs_unpaid"]) == {"paid", "unpaid"})

    r = client.get("/api/dashboard/activity")
    check("activity 200", r.status_code == 200)
    if r.status_code == 200:
        check("activity has items", r.json()["total"] > 0)

    print("\n== BillBell ==")
    r = client.get("/api/bills/summary")
    check("summary 200", r.status_code == 200)

    r = client.get("/api/bills", params={"page_size": 5})
    check("list 200", r.status_code == 200)
    total_before = r.json()["total"]

    r = client.post("/api/bills", json={
        "bill_name": "Smoke Test Bill",
        "category": "other",
        "amount": "10.50",
        "currency": "INR",
        "due_date": (today + timedelta(days=5)).isoformat(),
    })
    check("create 201", r.status_code == 201, r.text[:200])
    bill_id = r.json()["id"] if r.status_code == 201 else None

    if bill_id:
        r = client.post("/api/bills", json={
            "bill_name": "Bad", "category": "other", "amount": "-5", "due_date": today.isoformat(),
        })
        check("negative amount rejected 422", r.status_code == 422, str(r.status_code))

        r = client.post("/api/bills", json={
            "bill_name": "Bad", "category": "not_a_category", "amount": "5", "due_date": today.isoformat(),
        })
        check("bad category rejected 422", r.status_code == 422, str(r.status_code))

        r = client.get(f"/api/bills/{bill_id}")
        check("get one 200", r.status_code == 200)

        r = client.patch(f"/api/bills/{bill_id}", json={"bill_name": "Smoke Renamed"})
        check("patch 200", r.status_code == 200 and r.json()["bill_name"] == "Smoke Renamed")

        r = client.post(f"/api/bills/{bill_id}/pay", json={})
        check("pay 200", r.status_code == 200)
        check("pay sets status+date", r.json()["status"] == "paid" and r.json()["payment_date"], r.text[:150])

        r = client.post(f"/api/bills/{bill_id}/unpay", json={})
        check("unpay 200", r.status_code == 200 and r.json()["status"] in ("unpaid", "overdue"))

        r = client.get(f"/api/bills/{bill_id}")
        check("delete 200", r.status_code == 200)

    r = client.get("/api/bills/999999")
    check("missing bill 404", r.status_code == 404, str(r.status_code))

    print("\n== DateGuard ==")
    r = client.get("/api/documents/summary")
    check("summary 200", r.status_code == 200)

    r = client.get("/api/documents/expiring", params={"within_days": 30})
    check("expiring 200", r.status_code == 200)
    if r.status_code == 200:
        docs = r.json()
        check("expiring list non-empty", len(docs) > 0)
        masked = all(d.get("document_number") is None for d in docs)
        check("numbers masked in list", masked)

    r = client.post("/api/documents", json={
        "document_name": "Smoke Test Doc",
        "document_type": "certificate",
        "document_number": "CERT-SMOKE-998877",
        "expiry_date": (today + timedelta(days=10)).isoformat(),
        "reminder_days_before": 20,
    })
    check("create 201", r.status_code == 201, r.text[:200])
    doc_id = r.json()["id"] if r.status_code == 201 else None

    if doc_id:
        r = client.get(f"/api/documents/{doc_id}")
        check("get 200", r.status_code == 200)
        if r.status_code == 200:
            doc = r.json()
            check("status derived = expiring_soon", doc["status"] == "expiring_soon", doc["status"])
            check("days_remaining correct", doc["days_remaining"] == 10, str(doc["days_remaining"]))
            check("single view shows full number", doc["document_number"] == "CERT-SMOKE-998877")
            check("list view masks the number", doc["masked_document_number"].endswith("8877"))

        r = client.post(f"/api/documents/{doc_id}/renew", json={
            "new_expiry_date": (today + timedelta(days=400)).isoformat(),
        })
        check("renew 200", r.status_code == 200, r.text[:200])
        if r.status_code == 200:
            check("renew keeps history", len(r.json()["renewals"]) == 1)

        r = client.post(f"/api/documents/{doc_id}/renew", json={
            "new_expiry_date": (today - timedelta(days=10)).isoformat(),
        })
        check("backwards renewal rejected 400", r.status_code == 400, str(r.status_code))

        check("delete 200", client.delete(f"/api/documents/{doc_id}").status_code == 200)

    print("\n== DoseNote ==")
    r = client.get("/api/medications/today")
    check("today 200", r.status_code == 200, r.text[:200])
    if r.status_code == 200:
        today_data = r.json()
        check("today has doses", today_data["total_doses"] > 0, r.text[:150])

    r = client.post("/api/medications", json={
        "medication_name": "Smoke Schedule",
        "dosage": "1",
        "dosage_unit": "tablet",
        "start_date": today.isoformat(),
        "scheduled_times": ["07:30", "19:30", "07:30"],
    })
    check("create schedule 201", r.status_code == 201, r.text[:200])
    if r.status_code == 201:
        sched = r.json()
        check("duplicate times collapsed", len(sched["scheduled_times"]) == 2, str(sched["scheduled_times"]))
        check("times sorted", str(sched["scheduled_times"]) == "['07:30:00', '19:30:00']")
        sid = sched["id"]

        r = client.post("/api/medications", json={
            "medication_name": "Bad", "dosage": "1",
            "start_date": today.isoformat(), "scheduled_times": [],
        })
        check("empty times rejected 422", r.status_code == 422, str(r.status_code))

        r = client.post("/api/medications", json={
            "medication_name": "Bad", "dosage": "1",
            "start_date": today.isoformat(), "scheduled_times": ["25:99"],
        })
        check("invalid time rejected 422", r.status_code == 422, str(r.status_code))

        r = client.post(f"/api/medications/{sid}/doses", json={"scheduled_time": "07:30"})
        check("create dose 201", r.status_code == 201, r.text[:200])
        dose_id = r.json()["id"] if r.status_code == 201 else None

        if dose_id:
            r = client.post(f"/api/medications/{sid}/doses", json={"scheduled_time": "07:30"})
            check("duplicate dose blocked 409", r.status_code == 409, str(r.status_code))

            r = client.post(f"/api/medications/{sid}/doses", json={"scheduled_time": "12:00"})
            check("non-schedule time rejected 400", r.status_code == 400, str(r.status_code))

            r = client.patch(f"/api/doses/{dose_id}", json={"status": "taken"})
            check("mark taken 200", r.status_code == 200 and r.json()["status"] == "taken")
            check("taken_at recorded", r.json().get("taken_at") is not None)

            r = client.patch(f"/api/doses/{dose_id}", json={"status": "pending"})
            check("revert to pending 200", r.status_code == 200 and r.json()["status"] == "pending")
            check("taken_at cleared", r.json().get("taken_at") is None)

        r = client.get("/api/medications/adherence", params={"days": 7})
        check("adherence 200", r.status_code == 200)
        if r.status_code == 200:
            check("adherence has 7 days", len(r.json()["daily"]) == 7)

        r = client.get("/api/medications/history")
        check("history 200", r.status_code == 200)

        check("delete schedule 200", client.delete(f"/api/medications/{sid}").status_code == 200)

    print("\n== AquaHabit ==")
    r = client.get("/api/hydration/today")
    check("today 200", r.status_code == 200, r.text[:200])
    if r.status_code == 200:
        h = r.json()
        check("today total from DB", h["total_ml"] > 0, str(h["total_ml"]))
        check("percent computed", h["percent_complete"] > 0)

    r = client.post("/api/hydration/intake", json={"amount_ml": 250})
    check("create intake 201", r.status_code == 201, r.text[:200])
    entry_id = r.json()["id"] if r.status_code == 201 else None

    if entry_id:
        r = client.post("/api/hydration/intake", json={"amount_ml": 0})
        check("zero ml rejected 422", r.status_code == 422, str(r.status_code))

        r = client.post("/api/hydration/intake", json={"amount_ml": -100})
        check("negative ml rejected 422", r.status_code == 422, str(r.status_code))

        r = client.patch(f"/api/hydration/intake/{entry_id}", json={"amount_ml": 300})
        check("patch intake 200", r.status_code == 200 and r.json()["amount_ml"] == 300)

        check("delete intake 200", client.delete(f"/api/hydration/intake/{entry_id}").status_code == 200)

    r = client.get("/api/hydration/weekly")
    check("weekly 200", r.status_code == 200)
    if r.status_code == 200:
        w = r.json()
        check("weekly has 7 days", len(w["daily"]) == 7, str(len(w["daily"])))
        check("weekly average > 0", w["average_ml"] > 0)

    r = client.get("/api/hydration/monthly")
    check("monthly 200", r.status_code == 200)

    r = client.patch("/api/hydration/settings", json={"daily_goal_ml": 2600})
    check("settings update 200", r.status_code == 200 and r.json()["daily_goal_ml"] == 2600)
    client.patch("/api/hydration/settings", json={"daily_goal_ml": 2000})

    print("\n== Reminders ==")
    r = client.get("/api/reminders")
    check("reminders 200", r.status_code == 200, r.text[:200])
    if r.status_code == 200:
        rem = r.json()
        ids = [i["id"] for i in rem["items"]]
        check("no duplicate reminder ids", len(ids) == len(set(ids)), f"{len(ids)} vs {len(set(ids))}")
        dues = [i["due_at"] for i in rem["items"] if i["due_at"]]
        check("sorted by due date", dues == sorted(dues))
        check("modules combined", len({i["module"] for i in rem["items"]}) >= 2,
              str({i["module"] for i in rem["items"]}))
        check("groups populated", rem["total"] == len(rem["items"]))

    r = client.get("/api/reminders/summary")
    check("summary 200", r.status_code == 200)

    r = client.get("/api/reminders/upcoming")
    check("upcoming 200", r.status_code == 200)

    print("\n== Settings ==")
    r = client.get("/api/settings")
    check("settings 200", r.status_code == 200)
    r = client.patch("/api/settings", json={"theme": "dark"})
    check("theme update 200", r.status_code == 200 and r.json()["theme"] == "dark")
    client.patch("/api/settings", json={"theme": "light"})
    r = client.patch("/api/settings", json={"theme": "neon"})
    check("bad theme rejected 422", r.status_code == 422, str(r.status_code))

    print(f"\n{'=' * 52}\nPassed: {passed}   Failed: {len(failed)}")
    if failed:
        for name in failed:
            print(f"  - {name}")
        return 1
    print("All API smoke checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())