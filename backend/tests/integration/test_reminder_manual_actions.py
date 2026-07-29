"""Task 6.6 coverage: Admin manual cancel/reschedule of an individual
reminder instance, exercised through the real API — previously implemented
in app/api/v1/reminders.py with no test coverage at all."""

from datetime import date, datetime, timedelta, timezone


def _login(client, email, password):
    r = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def _auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


def _issue_invoice(client, headers, customer):
    r = client.post(
        "/api/v1/invoices",
        json={
            "customer_id": str(customer.id),
            "due_date": str(date.today() + timedelta(days=10)),
            "line_items": [{"description": "Widget", "quantity": "1", "unit_price": "10.00"}],
        },
        headers=headers,
    )
    assert r.status_code == 201, r.text
    invoice_id = r.json()["id"]
    r = client.post(f"/api/v1/invoices/{invoice_id}/issue", json={}, headers=headers)
    assert r.status_code == 200, r.text
    return invoice_id


def test_admin_can_cancel_a_single_reminder_instance(client, admin_user, finance_user, customer, active_tax_rate):
    finance_token = _login(client, finance_user.email, "FinancePass123!")
    invoice_id = _issue_invoice(client, _auth_headers(finance_token), customer)

    admin_token = _login(client, admin_user.email, "AdminPass123!")
    admin_headers = _auth_headers(admin_token)

    r = client.get(f"/api/v1/invoices/{invoice_id}/reminders", headers=admin_headers)
    assert r.status_code == 200, r.text
    instances = r.json()
    assert len(instances) == 5
    target = instances[0]
    assert target["status"] == "scheduled"

    r = client.post(
        f"/api/v1/invoices/{invoice_id}/reminders/{target['id']}/cancel",
        json={"reason": "customer requested no more reminders"},
        headers=admin_headers,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "cancelled"
    assert body["cancellation_reason"] == "customer requested no more reminders"
    assert body["cancelled_at"] is not None

    # Other instances remain untouched.
    r = client.get(f"/api/v1/invoices/{invoice_id}/reminders", headers=admin_headers)
    other_statuses = [ri["status"] for ri in r.json() if ri["id"] != target["id"]]
    assert all(status == "scheduled" for status in other_statuses)


def test_admin_can_reschedule_a_single_reminder_instance(client, admin_user, finance_user, customer, active_tax_rate):
    finance_token = _login(client, finance_user.email, "FinancePass123!")
    invoice_id = _issue_invoice(client, _auth_headers(finance_token), customer)

    admin_token = _login(client, admin_user.email, "AdminPass123!")
    admin_headers = _auth_headers(admin_token)

    r = client.get(f"/api/v1/invoices/{invoice_id}/reminders", headers=admin_headers)
    target = r.json()[0]
    new_time = (datetime.now(timezone.utc) + timedelta(days=100)).replace(microsecond=0)

    r = client.post(
        f"/api/v1/invoices/{invoice_id}/reminders/{target['id']}/reschedule",
        json={"new_scheduled_for": new_time.isoformat()},
        headers=admin_headers,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "scheduled"
    assert datetime.fromisoformat(body["scheduled_for"]) == new_time


def test_finance_staff_cannot_cancel_or_reschedule_reminders(client, finance_user, customer, active_tax_rate):
    finance_token = _login(client, finance_user.email, "FinancePass123!")
    headers = _auth_headers(finance_token)
    invoice_id = _issue_invoice(client, headers, customer)

    r = client.get(f"/api/v1/invoices/{invoice_id}/reminders", headers=headers)
    target = r.json()[0]

    r = client.post(
        f"/api/v1/invoices/{invoice_id}/reminders/{target['id']}/cancel",
        json={"reason": "not allowed"},
        headers=headers,
    )
    assert r.status_code == 403

    r = client.post(
        f"/api/v1/invoices/{invoice_id}/reminders/{target['id']}/reschedule",
        json={"new_scheduled_for": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()},
        headers=headers,
    )
    assert r.status_code == 403


def test_cancel_unknown_reminder_instance_returns_404(client, admin_user, finance_user, customer, active_tax_rate):
    finance_token = _login(client, finance_user.email, "FinancePass123!")
    invoice_id = _issue_invoice(client, _auth_headers(finance_token), customer)

    admin_token = _login(client, admin_user.email, "AdminPass123!")
    admin_headers = _auth_headers(admin_token)

    fake_id = "00000000-0000-0000-0000-000000000000"
    r = client.post(
        f"/api/v1/invoices/{invoice_id}/reminders/{fake_id}/cancel",
        json={"reason": "x"},
        headers=admin_headers,
    )
    assert r.status_code == 404
