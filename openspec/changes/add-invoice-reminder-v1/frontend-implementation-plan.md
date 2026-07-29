# React + TypeScript Frontend Implementation Plan — Invoice Generator & Payment-Reminder Engine

This plan is derived from the actual backend implementation in `backend/app/api/v1/*.py` and `backend/app/schemas/*.py` (not the original spec doc alone), plus the business rules in `openspec/changes/add-invoice-reminder-v1/specs/*/spec.md` and `invoice-reminder-spec.md` Section 13. All endpoint paths, payload shapes, status codes, and RBAC rules below were read directly from source, not inferred.

---

## 0. Ground truth extracted from the backend

**Base path:** all API routers are mounted under `/api/v1` (see `backend/app/main.py`). Health check is unauthenticated `GET /health` (no `/api/v1` prefix).

**Auth:** Bearer JWT via `Authorization: Bearer <token>` header (`HTTPBearer`, see `backend/app/api/deps.py`). No refresh-token endpoint exists — token expiry means a hard re-login. `POST /api/v1/auth/logout` is a no-op client-side discard (stateless tokens, no server session store).

**Roles (`UserRole`):** `admin`, `finance_staff`, `viewer` (`backend/app/models/user.py`). RBAC dependencies (`backend/app/core/permissions.py`):
- `require_any_role` (admin, finance_staff, viewer) — all GET/list/detail endpoints.
- `require_staff` (admin, finance_staff) — customer/invoice/payment create-edit-issue-cancel.
- `require_admin` (admin only) — tax rate creation, audit log, reminder cancel/reschedule, reminder kill-switch.

**Error contract:** every domain error returns `{"detail": string, "code": string}` via a single `DomainError` exception handler (`backend/app/core/exceptions.py`). Status codes used: `400` (validation/business rule), `401` (auth), `403` (RBAC), `404` (not found), `409` (duplicate payment warning only). Relevant `code` values the UI must special-case:
- `overpayment` (400)
- `edit_below_payments` (400)
- `invoice_not_editable` (400)
- `cancel_with_payments` (400)
- `customer_has_open_invoices` (400)
- `duplicate_payment_warning` (409) — not a hard error, requires user confirmation + resubmission
- `invalid_state_transition` (400)
- `authentication_error` (401)
- `authorization_error` (403)
- `not_found` (404)

**Invoice status enum:** `draft | issued | partially_paid | paid | cancelled`. `is_overdue` is a computed boolean returned on every `InvoiceRead` (never a stored status) — never render it as an editable field.

**Editability rule:** editable in `draft`, `issued`, `partially_paid`; blocked once `paid` or `cancelled`. Edits that would drop `total_amount` below `amount_paid` are rejected with `edit_below_payments`.

**Cancellation rule:** allowed only when `amount_paid == 0`, from `draft`, `issued`, `partially_paid`. Any invoice with `amount_paid > 0` gets `cancel_with_payments` on attempt — UI must proactively disable/explain, not just rely on the error.

**Issue rule:** only `draft → issued` via `POST /invoices/{id}/issue`; assigns `invoice_number`, snapshots tax rate and customer details, schedules reminders. Optional body `{"note": string}`.

**Payment rule:** `POST /invoices/{id}/payments?confirm_duplicate=<bool>`. If a same-amount payment was recorded on the same invoice in the last 60 minutes and `confirm_duplicate` is not set, backend returns `409 duplicate_payment_warning`. UI must show a confirm dialog and resubmit with `confirm_duplicate=true`. Overpayment (`amount_paid + amount > total_amount`) is a hard `400 overpayment`, never auto-allowed.

**Reminders:** read-only list for all roles; cancel/reschedule are **admin-only** (`require_admin`). `ReminderInstanceRead.status`: `scheduled | sending | sent | cancelled | failed`.

**Tax rates:** list is any-role; create is admin-only. Creating a new rate auto-supersedes the previously active one — no separate "deactivate" endpoint exists.

**Reports:** `GET /reports/aging` (no params), `GET /reports/collections?start=YYYY-MM-DD&end=YYYY-MM-DD` (required), `GET /reports/customer/{customer_id}`.

**Audit log:** admin-only, `GET /audit-log?entity_type=&entity_id=` (both optional filters), returns raw `before_state`/`after_state` JSON blobs plus `action` string and `actor_id`.

**System:** `POST /system/reminders/kill-switch` `{"enabled": bool}`, admin-only.

**No CORS middleware is configured on the backend.** For local dev, avoid the issue entirely with a Vite dev-server proxy (Section 8) rather than modifying the backend.

---

## 1. Tooling decisions

| Concern | Choice | Why |
|---|---|---|
| Build tool | **Vite** (`vite` + `@vitejs/plugin-react`) | fast dev server, trivial proxy config, TS support out of the box |
| Language | **TypeScript**, strict mode on | schemas map 1:1 to backend Pydantic models |
| Routing | **react-router-dom v6** (`createBrowserRouter`) | standard, protected-route wrapper is trivial |
| Data fetching / cache | **TanStack Query v5** | CRUD-heavy REST app with list/detail/invalidate patterns |
| Forms | **React Hook Form** + **Zod** (`@hookform/resolvers/zod`) | line-item builder needs array fields + numeric/decimal validation; RHF's `useFieldArray` is the right primitive |
| Styling | **Plain CSS Modules**, no Tailwind, no component library | internal staff tool; CSS Modules + a small shared `tokens.css` + a handful of primitives (`Button`, `Table`, `Badge`, `Modal`, `FormField`) in `src/components/ui/` |
| HTTP client | native `fetch` wrapped in a thin typed client | sufficient for this API's needs |
| State (client-only) | React Context for auth/session | no other global state library needed |
| Testing readiness | Vitest + React Testing Library for unit/component tests; `data-testid` conventions for Playwright E2E | |

Package baseline (`frontend/package.json`): `react`, `react-dom`, `react-router-dom`, `@tanstack/react-query`, `@tanstack/react-query-devtools` (dev), `react-hook-form`, `@hookform/resolvers`, `zod`, `date-fns`. Dev deps: `vite`, `@vitejs/plugin-react`, `typescript`, `vitest`, `@testing-library/react`, `@testing-library/user-event`, `eslint` + `@typescript-eslint/*`, `prettier`.

---

## 2. Repo layout

```
frontend/
  index.html
  vite.config.ts
  tsconfig.json
  .env.development          # VITE_API_BASE_URL=/api/v1 (proxied, see Section 8)
  .env.production           # VITE_API_BASE_URL=https://<prod-host>/api/v1
  package.json
  src/
    main.tsx                # ReactDOM.createRoot, QueryClientProvider, RouterProvider, AuthProvider
    App.tsx                 # top-level layout shell (nav + <Outlet/>)
    router.tsx               # createBrowserRouter tree, ProtectedRoute wrapping
    vite-env.d.ts

    api/
      client.ts             # fetchJson<T>() wrapper: base URL, auth header injection, error normalization
      auth.ts                # login(), logout() typed calls
      customers.ts           # list/create/get/update/delete
      invoices.ts             # list/create/get/update/issue/cancel
      payments.ts             # record/list (per invoice)
      reminders.ts             # list/cancel/reschedule (per invoice)
      taxRates.ts               # list/create
      reports.ts               # aging/collections/customerStatement
      dashboard.ts              # summary
      auditLog.ts               # list
      system.ts                 # killSwitch

    types/
      user.ts                # UserRole enum, UserRead, LoginRequest/Response
      customer.ts
      invoice.ts             # InvoiceStatus enum, LineItemCreate/Read, InvoiceRead, InvoiceCreate/Update
      payment.ts             # PaymentMethod enum, PaymentRead, PaymentCreateResponse
      reminder.ts             # ReminderInstanceStatus enum, ReminderInstanceRead
      taxRate.ts
      reports.ts
      audit.ts
      apiError.ts            # ApiError class + DomainErrorCode union type mirroring backend `code` values

    context/
      AuthContext.tsx        # user, token, login(), logout(), isAuthenticated; persists token to localStorage
      useAuth.ts             # hook

    hooks/
      useCustomers.ts        # useQuery/useMutation wrappers per resource (co-locate with TanStack Query keys)
      useInvoices.ts
      usePayments.ts
      useReminders.ts
      useTaxRates.ts
      useReports.ts
      useDashboard.ts
      useAuditLog.ts
      useRole.ts             # convenience: isAdmin/isStaff/isViewer/canEdit booleans from AuthContext

    components/
      ui/                    # Button, Input, Select, TextArea, Table, Badge, Modal, ConfirmDialog, Toast/ErrorBanner, Spinner, EmptyState
      layout/
        AppShell.tsx         # nav bar (role-aware links), page container
        ProtectedRoute.tsx   # redirects to /login if !isAuthenticated
        RoleGate.tsx         # <RoleGate roles={['admin']}>...</RoleGate> — hides/disables children
      invoices/
        LineItemBuilder.tsx  # useFieldArray-based dynamic row editor, shared by Create + Edit
        InvoiceStatusBadge.tsx
        PaymentHistoryTable.tsx
        ReminderHistoryTable.tsx
        PaymentForm.tsx
        CancelInvoiceDialog.tsx
      customers/
        CustomerForm.tsx
      common/
        ErrorBanner.tsx      # renders ApiError.detail + code consistently
        DecimalInput.tsx     # numeric input constrained to 2dp, used for money fields

    pages/
      LoginPage.tsx
      DashboardPage.tsx
      customers/
        CustomerListPage.tsx
        CustomerDetailPage.tsx     # includes create/edit inline
      invoices/
        InvoiceListPage.tsx
        InvoiceCreatePage.tsx
        InvoiceDetailPage.tsx      # composes line items, payment history+form, reminder history, issue/cancel/edit actions
        InvoiceEditPage.tsx
      taxRates/
        TaxRatePage.tsx
      reports/
        AgingReportPage.tsx
        CollectionsReportPage.tsx
        CustomerStatementPage.tsx
      audit/
        AuditLogPage.tsx
      NotFoundPage.tsx

    utils/
      money.ts               # format Decimal-as-string amounts for display (never do float math client-side on money)
      date.ts                 # IST-aware date formatting helpers
      apiErrorMessages.ts     # map DomainErrorCode -> human-readable fallback copy when detail is terse

  tests/
    setup.ts
```

---

## 3. API client layer

### 3.1 Core wrapper (`src/api/client.ts`)

```ts
export class ApiError extends Error {
  constructor(public status: number, public code: string, public detail: string) { super(detail); }
}

const BASE_URL = import.meta.env.VITE_API_BASE_URL; // e.g. "/api/v1"

async function request<T>(path: string, opts: RequestInit = {}): Promise<T> {
  const token = getStoredToken();
  const res = await fetch(`${BASE_URL}${path}`, {
    ...opts,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(opts.headers ?? {}),
    },
  });
  if (!res.ok) {
    let body: { detail?: string; code?: string } = {};
    try { body = await res.json(); } catch { /* non-JSON error body */ }
    const err = new ApiError(res.status, body.code ?? 'unknown_error', body.detail ?? res.statusText);
    if (res.status === 401) { clearStoredToken(); }
    throw err;
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export const get = <T>(path: string) => request<T>(path);
export const post = <T>(path: string, body?: unknown) => request<T>(path, { method: 'POST', body: body ? JSON.stringify(body) : undefined });
export const patch = <T>(path: string, body: unknown) => request<T>(path, { method: 'PATCH', body: JSON.stringify(body) });
export const del = <T>(path: string) => request<T>(path, { method: 'DELETE' });
```

Token storage: `localStorage.getItem('invoice_reminder.access_token')`. On login success, store token + user. On any `401` from `request()`, clear storage and let `AuthContext` redirect to `/login`. Because tokens are stateless JWTs with no refresh endpoint, a 401 always means "log in again."

### 3.2 Typed endpoint modules (exact paths as implemented)

**Auth** (`api/auth.ts`)
- `POST /auth/login` — body `{email, password}` → `{access_token, token_type, user: UserRead}`
- `POST /auth/logout` — client-side only; fire-and-forget

**Customers** (`api/customers.ts`) — under `/customers`
- `GET /customers` → `CustomerRead[]` (any role)
- `POST /customers` — body `{name, email, phone?, billing_address}` → `CustomerRead` (staff+)
- `GET /customers/{id}` → `CustomerRead` (any role)
- `PATCH /customers/{id}` — partial → `CustomerRead` (staff+)
- `DELETE /customers/{id}` → `CustomerRead` (staff+) — soft-delete/deactivate; may fail with `customer_has_open_invoices` (400)

**Invoices** (`api/invoices.ts`) — under `/invoices`
- `GET /invoices?status=&customer_id=` → `InvoiceRead[]` (any role)
- `POST /invoices` — body `{customer_id, due_date, line_items: [{description, quantity, unit_price}]}` → `InvoiceRead` (staff+)
- `GET /invoices/{id}` → `InvoiceRead` (any role, includes `line_items`)
- `PATCH /invoices/{id}` — body `{due_date?, line_items?}` (full replace when provided) → `InvoiceRead` (staff+); 400 `invoice_not_editable` / `edit_below_payments` possible
- `POST /invoices/{id}/issue` — body `{note?}` optional → `InvoiceRead` (staff+); 400 `invalid_state_transition` if not draft
- `POST /invoices/{id}/cancel` — body `{reason: string}` (required) → `InvoiceRead` (staff+); 400 `cancel_with_payments` / `invalid_state_transition`

**Payments** (`api/payments.ts`) — under `/invoices/{invoice_id}/payments`
- `POST /invoices/{id}/payments?confirm_duplicate=false` — body `{amount, payment_date, method, notes?, confirm_duplicate?}` → `PaymentCreateResponse { payment, duplicate_warning, duplicate_of }` (staff+). `method` is one of `cash | bank_transfer | upi | cheque`.
- `GET /invoices/{id}/payments` → `PaymentRead[]` (any role)

**Reminders** (`api/reminders.ts`) — under `/invoices/{invoice_id}/reminders`
- `GET /invoices/{id}/reminders` → `ReminderInstanceRead[]` (any role)
- `POST /invoices/{id}/reminders/{reminder_id}/cancel` — body `{reason?}` → `ReminderInstanceRead` (admin only)
- `POST /invoices/{id}/reminders/{reminder_id}/reschedule` — body `{new_scheduled_for: ISO datetime}` → `ReminderInstanceRead` (admin only)

**Tax rates** (`api/taxRates.ts`) — under `/tax-rates`
- `GET /tax-rates` → `TaxRateRead[]` (any role)
- `POST /tax-rates` — body `{name, rate_percent, effective_from}` → `TaxRateRead` (admin only) — supersedes the current active rate automatically

**Dashboard** (`api/dashboard.ts`)
- `GET /dashboard/summary` → `{total_outstanding, overdue_count, upcoming_due: InvoiceRead[], recent_payments: PaymentRead[]}` (any role)

**Reports** (`api/reports.ts`) — under `/reports`
- `GET /reports/aging` → `{buckets: [{range_label, invoices: InvoiceRead[], total}]}` (any role)
- `GET /reports/collections?start=YYYY-MM-DD&end=YYYY-MM-DD` → `{period_start, period_end, payments: PaymentRead[], total}` (any role, both params required)
- `GET /reports/customer/{customer_id}` → `{customer: CustomerRead, invoices: InvoiceRead[], payments: PaymentRead[]}` (any role)

**Audit log** (`api/auditLog.ts`)
- `GET /audit-log?entity_type=&entity_id=` → `AuditLogEntryRead[]` (admin only, both filters optional)

**System** (`api/system.ts`)
- `POST /system/reminders/kill-switch` — body `{enabled: boolean}` → `{enabled: boolean}` (admin only)

### 3.3 TanStack Query key conventions
`['customers']`, `['customers', id]`, `['invoices', {status, customerId}]`, `['invoices', id]`, `['invoices', id, 'payments']`, `['invoices', id, 'reminders']`, `['taxRates']`, `['dashboard']`, `['reports', 'aging']`, `['reports', 'collections', start, end]`, `['reports', 'customer', id]`, `['auditLog', {entityType, entityId}]`. Mutations invalidate the relevant keys (e.g. recording a payment invalidates invoice detail, invoice's payments, invoice list, and dashboard summary).

---

## 4. Auth / session handling

- `AuthContext` holds `{ user: UserRead | null, token: string | null, isLoading: boolean }` plus `login(email, password)` and `logout()`. On mount, hydrate from `localStorage`; treat the stored `user.role` as UI-hint only — the backend re-checks RBAC on every call regardless.
- No `/auth/me` endpoint exists. Store the `user` object alongside the token in `localStorage`. On app load, optimistically treat a stored session as valid and let the first API call's `401` clear it and redirect.
- `ProtectedRoute`: if `!isAuthenticated`, `<Navigate to="/login" replace state={{from: location}} />`.
- `RoleGate roles={[...]}`: renders children only if `user.role` is allowed; a `disabled` variant renders children but disabled with a tooltip ("Admin only").
- Role-based UI gating map (from `permissions.py`):
  - Viewer: Dashboard, Customers (read), Invoices (read), Reports, Tax Rates (read). No create/edit/issue/cancel, no payment form, no reminder cancel/reschedule, no Audit Log nav entry.
  - Finance Staff: everything Viewer has, plus customer create/edit/delete, invoice create/edit/issue/cancel, payment recording. No Audit Log, no tax rate creation, no reminder cancel/reschedule, no kill switch.
  - Admin: everything, plus Audit Log, Tax Rate creation, reminder cancel/reschedule, kill switch.

---

## 5. Pages / routes

Router tree (all except `/login` wrapped in `ProtectedRoute` + `AppShell`):

| Route | Page | Data / actions |
|---|---|---|
| `/login` | `LoginPage` | form → `POST /auth/login`; on success store session, redirect to `/` or `location.state.from` |
| `/` | `DashboardPage` | `GET /dashboard/summary`; total outstanding, overdue count, upcoming-due table, recent payments table |
| `/customers` | `CustomerListPage` | `GET /customers`; table; "New Customer" (staff+) → `POST /customers` |
| `/customers/:id` | `CustomerDetailPage` | `GET /customers/:id`; inline edit (staff+) → `PATCH`; "Deactivate" (staff+) → `DELETE`, surfaces `customer_has_open_invoices` inline; link to statement report and invoices |
| `/invoices` | `InvoiceListPage` | `GET /invoices?status=&customer_id=`; status/customer filters; table of invoice_number/status/overdue/total/amount_paid/due_date; "New Invoice" (staff+) |
| `/invoices/new` | `InvoiceCreatePage` | customer picker, due date, `LineItemBuilder` → `POST /invoices`; navigate to detail on success |
| `/invoices/:id` | `InvoiceDetailPage` | `GET /invoices/:id` + payments + reminders. Header (status/overdue badges, invoice_number or "Draft"), customer snapshot, line items, totals, action bar (Edit/Issue/Cancel, staff+), `PaymentHistoryTable` + `PaymentForm`, `ReminderHistoryTable` with admin-only actions |
| `/invoices/:id/edit` | `InvoiceEditPage` | `LineItemBuilder` + due date, pre-filled; redirect back with banner if not editable → `PATCH /invoices/:id`; inline `edit_below_payments` error with computed context |
| `/tax-rates` | `TaxRatePage` | `GET /tax-rates` list with active rate highlighted; create form admin-only → `POST /tax-rates` |
| `/reports/aging` | `AgingReportPage` | `GET /reports/aging`; collapsible bucket sections |
| `/reports/collections` | `CollectionsReportPage` | date-range form → `GET /reports/collections?start=&end=`; payments table + total |
| `/reports/customer/:customerId` | `CustomerStatementPage` | `GET /reports/customer/:id` |
| `/audit-log` | `AuditLogPage` | admin-only route (redirect non-admins); filters, expandable before/after JSON diff view |
| `*` | `NotFoundPage` | — |

### Invoice detail action gating detail
- **Edit**: visible staff+; disabled with tooltip when `status in (paid, cancelled)`.
- **Issue**: visible staff+ only when `status === 'draft'`.
- **Cancel**: visible staff+ only when `status in (draft, issued, partially_paid)`; disabled with tooltip when `amount_paid > 0` (pre-empt `cancel_with_payments`). Opens `CancelInvoiceDialog` requiring non-empty `reason` → `POST /invoices/:id/cancel`.
- **Record Payment**: visible staff+, only when `status in (issued, partially_paid)`. On `409 duplicate_payment_warning`, open `ConfirmDialog`; on confirm, resubmit with `confirm_duplicate=true`. On `overpayment` 400, show inline error with computed max-allowed amount (`total_amount - amount_paid`).
- **Reminders** row actions (Cancel/Reschedule): rendered for all roles, enabled only for Admin (`RoleGate` disabled-variant); actionable only when `status === 'scheduled'`.

---

## 6. Error / loading state conventions

- **Loading:** every page-level query uses `isLoading`/`isPending` to show a shared `<Spinner/>`/skeleton; never a blank page.
- **Query errors:** shared `<ErrorBanner error={error}/>` with a "Retry" button. `403` shows "You don't have permission to view this."
- **Mutation errors:** surfaced inline near the triggering form/button, never a global toast for 400s. Map `ApiError.code` through `utils/apiErrorMessages.ts` for `overpayment`, `edit_below_payments`, `cancel_with_payments`, `duplicate_payment_warning`, `customer_has_open_invoices`; fall back to `ApiError.detail` verbatim otherwise.
- **401 handling:** `client.ts` clears stored session on any 401; TanStack Query's global `QueryCache`/`MutationCache` `onError` callbacks check `error instanceof ApiError && error.status === 401` and imperatively redirect to `/login`.
- **Confirmation flows** (cancel invoice, duplicate payment, customer deactivate): always a modal requiring explicit confirm, never a bare browser `confirm()`.
- **Toasts** (success/info — "Invoice issued", "Payment recorded", "Tax rate created"): lightweight shared toast, auto-dismiss ~4s, one at a time.

---

## 7. Build order (phased, with validation gates)

**Phase 0 — Scaffold, API client, auth**
- Vite + TS scaffold, folder structure, lint/format config, `.env.development` with Vite proxy.
- `client.ts` + `ApiError`, all typed endpoint modules and `types/*.ts`.
- `AuthContext`, `LoginPage`, `ProtectedRoute`, `AppShell` (nav shell, role-aware links, page stubs).
- **Gate:** can log in against the real backend (seeded users), token persists across refresh, protected route while logged out redirects to `/login`, logout clears session and redirects.

**Phase 1 — Dashboard + Customers**
- `DashboardPage` wired to `/dashboard/summary`. Customer list/detail/create/edit/deactivate, full RBAC gating.
- **Gate:** Admin/FinanceStaff can create/edit/deactivate customers; Viewer sees same data with no mutating controls; `customer_has_open_invoices` surfaces correctly.

**Phase 2 — Invoices: list, create, detail (read side)**
- `InvoiceListPage` with filters, `InvoiceCreatePage` with `LineItemBuilder`, `InvoiceDetailPage` (read-only, incl. read-only payment/reminder history).
- **Gate:** create a multi-line-item draft invoice, confirm `draft` status with no `invoice_number`, totals match line item math; filter list by status and customer.

**Phase 3 — Invoice edit / issue / cancel**
- `InvoiceEditPage`, Issue action, Cancel action + `CancelInvoiceDialog`, full action-gating.
- **Gate:** edit a draft (succeeds), issue it (`invoice_number` assigned, tax snapshot applied, status → `issued`), edit a `paid` invoice blocked (button pre-emptively disabled), edit below `amount_paid` on a partially-paid invoice shows inline `edit_below_payments`, cancel with payments blocked (disabled + tooltip), cancel a clean draft (reason required, succeeds).

**Phase 4 — Payments**
- `PaymentForm`, `PaymentHistoryTable`, duplicate-payment confirm flow, overpayment inline error.
- **Gate:** partial payment (status → `partially_paid`), remaining balance (status → `paid`, Edit/Cancel now disabled), overpayment blocked with clear messaging, two identical-amount payments within an hour trigger duplicate confirm on the second.

**Phase 5 — Reminders**
- `ReminderHistoryTable` with admin-gated cancel/reschedule.
- **Gate:** Viewer/FinanceStaff see visible-but-disabled reminder actions; Admin can cancel/reschedule; cancelling the invoice cascades to cancel remaining reminders (verify via this table after Phase 3's cancel flow).

**Phase 6 — Tax rates, Reports, Audit log**
- `TaxRatePage`, `AgingReportPage`, `CollectionsReportPage`, `CustomerStatementPage`, `AuditLogPage`.
- **Gate:** non-admin cannot reach `/audit-log` (redirected, no nav entry) or submit tax-rate create form; new tax rate supersedes the old one in list view; all three reports render real data end-to-end.

**Phase 7 — Polish + Playwright readiness**
- Loading/error/empty state audit across all pages.
- `data-testid` conventions on every actionable element and key data cell:
  - `data-testid="invoice-row-{id}"`, `"invoice-status-badge"`, `"invoice-total"`
  - `"btn-issue-invoice"`, `"btn-cancel-invoice"`, `"btn-edit-invoice"`
  - `"payment-form-amount"`, `"payment-form-submit"`, `"duplicate-payment-confirm"`
  - `"reminder-row-{id}"`, `"btn-cancel-reminder-{id}"`, `"btn-reschedule-reminder-{id}"`
  - `"error-banner"` (single consistent testid across all pages/forms)
  - `"nav-audit-log"` (for asserting absence for non-admins)
  - Form fields: `"field-{name}"` on the input wrapper.
- Basic Vitest component tests for `LineItemBuilder`, `PaymentForm` duplicate-confirm branch, `RoleGate`.
- **Gate:** a smoke Playwright script can log in as each of the 3 seeded roles and assert correct nav/actions are visible using only `data-testid` hooks — no reliance on text content or CSS classes.

---

## 8. Local dev setup

`frontend/vite.config.ts`:
```ts
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api/v1': { target: 'http://localhost:8000', changeOrigin: true },
      '/health': { target: 'http://localhost:8000', changeOrigin: true },
    },
  },
});
```

`frontend/.env.development`:
```
VITE_API_BASE_URL=/api/v1
```
(so `fetch` calls go to same-origin `/api/v1/...`, proxied by Vite to FastAPI on `http://localhost:8000` — sidesteps the lack of CORS middleware without touching backend code.)

Running locally: start backend per `backend/README.md` (`uvicorn app.main:app --reload`, port 8000, Postgres+Redis per that README), then `cd frontend && npm install && npm run dev` (served on `http://localhost:5173`). Check `backend/seed/` for seeded per-role credentials for manual phase-gate testing.

---

### Critical Files for Implementation
- backend/app/api/v1/invoices.py
- backend/app/api/v1/payments.py
- backend/app/core/exceptions.py
- backend/app/core/permissions.py
- backend/app/schemas/invoice.py
