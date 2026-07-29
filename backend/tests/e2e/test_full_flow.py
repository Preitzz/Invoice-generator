"""Placeholder for browser-level E2E (Playwright), per implementation-plan.md
Section 10: "v1 has no bundled frontend yet, so tests/e2e/ is a placeholder —
true Playwright browser E2E only makes sense once a frontend exists."

`tests/integration/` (httpx/TestClient against the live FastAPI app) is the
effective end-to-end coverage for this backend-only pass — see in particular
test_invoice_lifecycle.py, which exercises the full draft -> issue ->
partial-payment -> full-payment -> reminders-auto-cancelled flow via the
real HTTP API surface against a real Postgres database.
"""

import pytest


@pytest.mark.skip(
    reason="No frontend exists yet in v1 — browser E2E is deferred until one is built. "
    "See tests/integration/test_invoice_lifecycle.py for the equivalent API-level flow."
)
def test_full_flow_placeholder():
    pass
