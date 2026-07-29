from datetime import date, timedelta
from decimal import Decimal


def _login(client, email, password):
    r = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def _auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


def _create_and_issue(client, headers, customer_id, due_date, unit_price="100.00"):
    r = client.post(
        "/api/v1/invoices",
        json={
            "customer_id": str(customer_id),
            "due_date": str(due_date),
            "line_items": [{"description": "Widget", "quantity": "1", "unit_price": unit_price}],
        },
        headers=headers,
    )
    assert r.status_code == 201, r.text
    invoice_id = r.json()["id"]
    r = client.post(f"/api/v1/invoices/{invoice_id}/issue", json={}, headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


def test_aging_report_buckets_outstanding_invoices_by_days_overdue(
    client, finance_user, customer, active_tax_rate, db_session
):
    from app.models.invoice import Invoice

    token = _login(client, finance_user.email, "FinancePass123!")
    headers = _auth_headers(token)

    issued_45 = _create_and_issue(client, headers, customer.id, date.today() - timedelta(days=45))
    # Force it into the 31-60 bucket by rewriting due_date directly (past
    # issue-time due dates aren't creatable through the validated API since
    # nothing stops it, but let's be explicit and deterministic).
    inv = db_session.get(Invoice, issued_45["id"])
    inv.due_date = date.today() - timedelta(days=45)
    db_session.commit()

    r = client.get("/api/v1/reports/aging", headers=headers)
    assert r.status_code == 200, r.text
    report = r.json()
    labels = [b["range_label"] for b in report["buckets"]]
    assert labels == ["0-30", "31-60", "61-90", "90+"]

    bucket_31_60 = next(b for b in report["buckets"] if b["range_label"] == "31-60")
    ids_in_bucket = {inv_["id"] for inv_ in bucket_31_60["invoices"]}
    assert issued_45["id"] in ids_in_bucket


def test_aging_report_excludes_paid_and_cancelled(client, finance_user, customer, active_tax_rate, db_session):
    from app.models.invoice import Invoice

    token = _login(client, finance_user.email, "FinancePass123!")
    headers = _auth_headers(token)

    issued = _create_and_issue(client, headers, customer.id, date.today() - timedelta(days=10))
    inv = db_session.get(Invoice, issued["id"])
    inv.due_date = date.today() - timedelta(days=10)
    db_session.commit()

    client.post(
        f"/api/v1/invoices/{issued['id']}/payments",
        json={"amount": issued["total_amount"], "payment_date": str(date.today()), "method": "cash"},
        headers=headers,
    )

    r = client.get("/api/v1/reports/aging", headers=headers)
    all_invoice_ids = {
        inv_["id"] for bucket in r.json()["buckets"] for inv_ in bucket["invoices"]
    }
    assert issued["id"] not in all_invoice_ids


def test_collections_report_filters_by_date_range(client, finance_user, customer, active_tax_rate):
    token = _login(client, finance_user.email, "FinancePass123!")
    headers = _auth_headers(token)

    issued = _create_and_issue(client, headers, customer.id, date.today() + timedelta(days=10))

    old_date = date.today() - timedelta(days=100)
    recent_date = date.today() - timedelta(days=1)

    client.post(
        f"/api/v1/invoices/{issued['id']}/payments",
        json={"amount": "10.00", "payment_date": str(old_date), "method": "cash"},
        headers=headers,
    )
    client.post(
        f"/api/v1/invoices/{issued['id']}/payments",
        json={"amount": "20.00", "payment_date": str(recent_date), "method": "upi"},
        headers=headers,
    )

    start = date.today() - timedelta(days=5)
    end = date.today()
    r = client.get(
        "/api/v1/reports/collections", params={"start": str(start), "end": str(end)}, headers=headers
    )
    assert r.status_code == 200, r.text
    report = r.json()
    payment_dates = [p["payment_date"] for p in report["payments"]]
    assert str(recent_date) in payment_dates
    assert str(old_date) not in payment_dates
    assert Decimal(report["total"]) == Decimal("20.00")


def test_customer_statement_includes_all_invoice_statuses(
    client, finance_user, customer, active_tax_rate
):
    token = _login(client, finance_user.email, "FinancePass123!")
    headers = _auth_headers(token)

    issued_and_paid = _create_and_issue(client, headers, customer.id, date.today() + timedelta(days=10))
    client.post(
        f"/api/v1/invoices/{issued_and_paid['id']}/payments",
        json={"amount": issued_and_paid["total_amount"], "payment_date": str(date.today()), "method": "cash"},
        headers=headers,
    )

    r = client.post(
        "/api/v1/invoices",
        json={
            "customer_id": str(customer.id),
            "due_date": str(date.today() + timedelta(days=20)),
            "line_items": [{"description": "Widget", "quantity": "1", "unit_price": "10.00"}],
        },
        headers=headers,
    )
    draft_for_cancel_id = r.json()["id"]
    issued_for_cancel = client.post(
        f"/api/v1/invoices/{draft_for_cancel_id}/issue", json={}, headers=headers
    ).json()
    client.post(
        f"/api/v1/invoices/{issued_for_cancel['id']}/cancel", json={"reason": "test"}, headers=headers
    )

    r = client.get(f"/api/v1/reports/customer/{customer.id}", headers=headers)
    assert r.status_code == 200, r.text
    statement = r.json()
    invoice_ids = {inv["id"] for inv in statement["invoices"]}
    assert issued_and_paid["id"] in invoice_ids
    assert issued_for_cancel["id"] in invoice_ids
    statuses = {inv["status"] for inv in statement["invoices"]}
    assert "paid" in statuses
    assert "cancelled" in statuses


def test_no_tax_summary_report_endpoint_exists(client, finance_user):
    token = _login(client, finance_user.email, "FinancePass123!")
    headers = _auth_headers(token)
    r = client.get("/api/v1/reports/tax-summary", headers=headers)
    assert r.status_code == 404
