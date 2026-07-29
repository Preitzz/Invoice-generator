from datetime import date, timedelta


def _login(client, email, password):
    r = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def _auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


def test_login_success_issues_token(client, admin_user):
    token = _login(client, admin_user.email, "AdminPass123!")
    assert token


def test_login_failure_does_not_reveal_user_existence(client, admin_user):
    r1 = client.post("/api/v1/auth/login", json={"email": admin_user.email, "password": "wrong"})
    r2 = client.post("/api/v1/auth/login", json={"email": "nobody@example.com", "password": "wrong"})
    assert r1.status_code == 401
    assert r2.status_code == 401
    assert r1.json()["detail"] == r2.json()["detail"]


def test_no_sso_or_mfa_prompt_login_is_plain_username_password(client, admin_user):
    r = client.post("/api/v1/auth/login", json={"email": admin_user.email, "password": "AdminPass123!"})
    body = r.json()
    assert set(body.keys()) == {"access_token", "token_type", "user"}


def test_viewer_cannot_record_payment(client, viewer_user, customer, admin_user, active_tax_rate, db_session):
    from app.services import invoices as invoice_service
    from tests.factories import make_line_item

    draft = invoice_service.create_draft_invoice(
        db_session,
        customer_id=customer.id,
        due_date=date.today() + timedelta(days=10),
        line_items=[make_line_item()],
        actor_id=admin_user.id,
    )
    issued = invoice_service.issue_invoice(db_session, draft.id, actor_id=admin_user.id)

    token = _login(client, viewer_user.email, "ViewerPass123!")
    r = client.post(
        f"/api/v1/invoices/{issued.id}/payments",
        json={"amount": "10.00", "payment_date": str(date.today()), "method": "cash"},
        headers=_auth_headers(token),
    )
    assert r.status_code == 403


def test_viewer_can_read_customers(client, viewer_user):
    token = _login(client, viewer_user.email, "ViewerPass123!")
    r = client.get("/api/v1/customers", headers=_auth_headers(token))
    assert r.status_code == 200


def test_admin_can_use_kill_switch(client, admin_user):
    token = _login(client, admin_user.email, "AdminPass123!")
    r = client.post("/api/v1/system/reminders/kill-switch", json={"enabled": True}, headers=_auth_headers(token))
    assert r.status_code == 200
    assert r.json()["enabled"] is True


def test_finance_staff_cannot_use_kill_switch(client, finance_user):
    token = _login(client, finance_user.email, "FinancePass123!")
    r = client.post("/api/v1/system/reminders/kill-switch", json={"enabled": True}, headers=_auth_headers(token))
    assert r.status_code == 403


def test_finance_staff_can_manage_invoices_and_payments(client, finance_user, customer):
    token = _login(client, finance_user.email, "FinancePass123!")
    r = client.post(
        "/api/v1/invoices",
        json={
            "customer_id": str(customer.id),
            "due_date": str(date.today() + timedelta(days=10)),
            "line_items": [{"description": "Widget", "quantity": "1", "unit_price": "100.00"}],
        },
        headers=_auth_headers(token),
    )
    assert r.status_code == 201, r.text
    invoice_id = r.json()["id"]

    r = client.post(f"/api/v1/invoices/{invoice_id}/issue", json={}, headers=_auth_headers(token))
    assert r.status_code == 200, r.text

    r = client.post(
        f"/api/v1/invoices/{invoice_id}/payments",
        json={"amount": "50.00", "payment_date": str(date.today()), "method": "cash"},
        headers=_auth_headers(token),
    )
    assert r.status_code == 201, r.text


def test_unauthenticated_request_rejected(client):
    r = client.get("/api/v1/customers")
    assert r.status_code == 401


def test_audit_log_endpoint_admin_only(client, admin_user, finance_user):
    admin_token = _login(client, admin_user.email, "AdminPass123!")
    r = client.get("/api/v1/audit-log", headers=_auth_headers(admin_token))
    assert r.status_code == 200

    finance_token = _login(client, finance_user.email, "FinancePass123!")
    r = client.get("/api/v1/audit-log", headers=_auth_headers(finance_token))
    assert r.status_code == 403
