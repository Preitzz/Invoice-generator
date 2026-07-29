from datetime import date, timedelta


def _login(client, email, password):
    r = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def _auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


def test_full_invoice_lifecycle_draft_issue_pay(client, finance_user, customer, active_tax_rate):
    token = _login(client, finance_user.email, "FinancePass123!")
    headers = _auth_headers(token)

    r = client.post(
        "/api/v1/invoices",
        json={
            "customer_id": str(customer.id),
            "due_date": str(date.today() + timedelta(days=10)),
            "line_items": [
                {"description": "Widget", "quantity": "2", "unit_price": "100.00"},
                {"description": "Gadget", "quantity": "1", "unit_price": "50.00"},
            ],
        },
        headers=headers,
    )
    assert r.status_code == 201, r.text
    invoice = r.json()
    assert invoice["status"] == "draft"
    assert invoice["invoice_number"] is None
    invoice_id = invoice["id"]

    r = client.post(f"/api/v1/invoices/{invoice_id}/issue", json={}, headers=headers)
    assert r.status_code == 200, r.text
    issued = r.json()
    assert issued["status"] == "issued"
    assert issued["invoice_number"].startswith("INV-")
    total_amount = issued["total_amount"]

    r = client.get(f"/api/v1/invoices/{invoice_id}/reminders", headers=headers)
    assert r.status_code == 200
    assert len(r.json()) == 5

    r = client.post(
        f"/api/v1/invoices/{invoice_id}/payments",
        json={"amount": total_amount, "payment_date": str(date.today()), "method": "bank_transfer"},
        headers=headers,
    )
    assert r.status_code == 201, r.text

    r = client.get(f"/api/v1/invoices/{invoice_id}", headers=headers)
    assert r.status_code == 200
    final_invoice = r.json()
    assert final_invoice["status"] == "paid"
    assert final_invoice["amount_paid"] == total_amount

    r = client.get(f"/api/v1/invoices/{invoice_id}/reminders", headers=headers)
    statuses = {ri["status"] for ri in r.json()}
    assert statuses == {"cancelled"}


def test_overpayment_rejected_via_api(client, finance_user, customer, active_tax_rate):
    token = _login(client, finance_user.email, "FinancePass123!")
    headers = _auth_headers(token)

    r = client.post(
        "/api/v1/invoices",
        json={
            "customer_id": str(customer.id),
            "due_date": str(date.today() + timedelta(days=10)),
            "line_items": [{"description": "Widget", "quantity": "1", "unit_price": "10.00"}],
        },
        headers=headers,
    )
    invoice_id = r.json()["id"]
    client.post(f"/api/v1/invoices/{invoice_id}/issue", json={}, headers=headers)

    r = client.post(
        f"/api/v1/invoices/{invoice_id}/payments",
        json={"amount": "9999.00", "payment_date": str(date.today()), "method": "cash"},
        headers=headers,
    )
    assert r.status_code == 400
    assert r.json()["code"] == "overpayment"


def test_cancel_blocked_once_payment_recorded_via_api(client, finance_user, customer, active_tax_rate):
    token = _login(client, finance_user.email, "FinancePass123!")
    headers = _auth_headers(token)

    r = client.post(
        "/api/v1/invoices",
        json={
            "customer_id": str(customer.id),
            "due_date": str(date.today() + timedelta(days=10)),
            "line_items": [{"description": "Widget", "quantity": "1", "unit_price": "100.00"}],
        },
        headers=headers,
    )
    invoice_id = r.json()["id"]
    client.post(f"/api/v1/invoices/{invoice_id}/issue", json={}, headers=headers)
    client.post(
        f"/api/v1/invoices/{invoice_id}/payments",
        json={"amount": "10.00", "payment_date": str(date.today()), "method": "cash"},
        headers=headers,
    )

    r = client.post(
        f"/api/v1/invoices/{invoice_id}/cancel", json={"reason": "test"}, headers=headers
    )
    assert r.status_code == 400
    assert r.json()["code"] == "cancel_with_payments"


def test_draft_edit_then_issue_recomputes_totals(client, finance_user, customer, active_tax_rate):
    token = _login(client, finance_user.email, "FinancePass123!")
    headers = _auth_headers(token)

    r = client.post(
        "/api/v1/invoices",
        json={
            "customer_id": str(customer.id),
            "due_date": str(date.today() + timedelta(days=10)),
            "line_items": [{"description": "Widget", "quantity": "1", "unit_price": "10.00"}],
        },
        headers=headers,
    )
    invoice_id = r.json()["id"]

    r = client.patch(
        f"/api/v1/invoices/{invoice_id}",
        json={"line_items": [{"description": "Widget v2", "quantity": "2", "unit_price": "20.00"}]},
        headers=headers,
    )
    assert r.status_code == 200
    assert r.json()["subtotal"] == "40.00"
