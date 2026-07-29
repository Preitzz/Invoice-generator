from datetime import date, timedelta


def _login(client, email, password):
    r = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def _auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


def test_create_customer(client, finance_user):
    token = _login(client, finance_user.email, "FinancePass123!")
    r = client.post(
        "/api/v1/customers",
        json={"name": "Beta LLC", "email": "beta@example.com", "phone": "123", "billing_address": "1 Main St"},
        headers=_auth_headers(token),
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["is_active"] is True
    assert "id" in body


def test_delete_customer_with_no_open_invoices_soft_deletes(client, finance_user, customer):
    token = _login(client, finance_user.email, "FinancePass123!")
    headers = _auth_headers(token)

    r = client.delete(f"/api/v1/customers/{customer.id}", headers=headers)
    assert r.status_code == 200
    assert r.json()["is_active"] is False

    r = client.get(f"/api/v1/customers/{customer.id}", headers=headers)
    assert r.status_code == 200
    assert r.json()["is_active"] is False


def test_delete_customer_with_open_invoice_converts_to_soft_delete(
    client, finance_user, customer, active_tax_rate
):
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

    r = client.delete(f"/api/v1/customers/{customer.id}", headers=headers)
    assert r.status_code == 200
    assert r.json()["is_active"] is False

    # Historical invoice remains queryable, unaffected.
    r = client.get(f"/api/v1/invoices/{invoice_id}", headers=headers)
    assert r.status_code == 200
    assert r.json()["status"] == "issued"


def test_update_customer_does_not_touch_issued_invoice_snapshot(
    client, finance_user, customer, active_tax_rate
):
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
    issued = client.post(f"/api/v1/invoices/{invoice_id}/issue", json={}, headers=headers).json()

    client.patch(
        f"/api/v1/customers/{customer.id}",
        json={"email": "new-email@example.com"},
        headers=headers,
    )

    r = client.get(f"/api/v1/invoices/{invoice_id}", headers=headers)
    assert r.json()["customer_email_snapshot"] == issued["customer_email_snapshot"]
    assert r.json()["customer_email_snapshot"] != "new-email@example.com"
