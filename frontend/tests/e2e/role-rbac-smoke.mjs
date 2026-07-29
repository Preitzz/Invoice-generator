// Phase 7 smoke test: logs in as each of the 3 seeded roles (admin,
// finance_staff, viewer) and asserts correct nav/action visibility using
// only data-testid hooks, per the frontend implementation plan's Phase 7
// gate. Requires the backend (seeded) and `npm run dev` frontend running,
// plus `playwright` (with a chromium build) resolvable from this file —
// it is not a project devDependency, run it with a global/adjacent
// playwright install, e.g.:
//   node tests/e2e/role-rbac-smoke.mjs
import { chromium } from 'playwright';

const results = [];
function log(name, ok, extra) {
  results.push({ name, ok, extra });
  console.log(`${ok ? 'PASS' : 'FAIL'}: ${name}${extra ? ' — ' + extra : ''}`);
}

async function loginAs(page, email, password) {
  await page.goto('http://localhost:5173/login');
  await page.fill('[data-testid="login-email"]', email);
  await page.fill('[data-testid="login-password"]', password);
  await page.click('[data-testid="login-submit"]');
  await page.waitForURL((u) => u.pathname !== '/login', { timeout: 5000 }).catch(() => {});
  await page.locator('[data-testid="user-info"]').waitFor({ state: 'visible', timeout: 5000 });
}

const browser = await chromium.launch();

const roles = [
  {
    role: 'admin',
    email: 'admin@example.com',
    expectNavAuditLog: true,
    expectCustomerCreate: true,
    expectTaxRateForm: true,
  },
  {
    role: 'finance_staff',
    email: 'finance@example.com',
    expectNavAuditLog: false,
    expectCustomerCreate: true,
    expectTaxRateForm: false,
  },
  {
    role: 'viewer',
    email: 'viewer@example.com',
    expectNavAuditLog: false,
    expectCustomerCreate: false,
    expectTaxRateForm: false,
  },
];

for (const r of roles) {
  const page = await browser.newPage();
  await loginAs(page, r.email, 'ChangeMe123!');

  // Nav: audit log entry visible only for admin, using data-testid only.
  const navAuditCount = await page.locator('[data-testid="nav-audit-log"]').count();
  log(`[${r.role}] nav-audit-log presence matches RBAC`, (navAuditCount === 1) === r.expectNavAuditLog, `count=${navAuditCount}`);

  // Common nav entries present for every role.
  for (const navId of ['nav-dashboard', 'nav-customers', 'nav-invoices', 'nav-tax-rates', 'nav-reports']) {
    const count = await page.locator(`[data-testid="${navId}"]`).count();
    log(`[${r.role}] ${navId} visible`, count === 1);
  }

  // Customers page: create button gated by role.
  await page.goto('http://localhost:5173/customers');
  await page.locator('[data-testid="customer-list-page"]').waitFor({ timeout: 5000 });
  const createCount = await page.locator('[data-testid="btn-new-customer"]').count();
  log(`[${r.role}] btn-new-customer presence matches RBAC`, (createCount === 1) === r.expectCustomerCreate, `count=${createCount}`);

  // Tax rates page: create form gated to admin only.
  await page.goto('http://localhost:5173/tax-rates');
  await page.locator('[data-testid="tax-rate-page"]').waitFor({ timeout: 5000 });
  const taxFormCount = await page.locator('[data-testid="tax-rate-form"]').count();
  log(`[${r.role}] tax-rate-form presence matches RBAC`, (taxFormCount === 1) === r.expectTaxRateForm, `count=${taxFormCount}`);

  // Invoice list: New Invoice button gated to staff+.
  await page.goto('http://localhost:5173/invoices');
  await page.locator('[data-testid="invoice-list-page"]').waitFor({ timeout: 5000 });
  const newInvoiceCount = await page.locator('[data-testid="btn-new-invoice"]').count();
  const expectNewInvoice = r.role !== 'viewer';
  log(`[${r.role}] btn-new-invoice presence matches RBAC`, (newInvoiceCount === 1) === expectNewInvoice, `count=${newInvoiceCount}`);

  // Direct navigation to /audit-log: only admin should land there.
  await page.goto('http://localhost:5173/audit-log');
  await page.waitForTimeout(800);
  const onAuditLog = page.url().includes('/audit-log');
  log(`[${r.role}] direct /audit-log navigation matches RBAC`, onAuditLog === r.expectNavAuditLog, page.url());

  await page.close();
}

await browser.close();

const failed = results.filter((r) => !r.ok);
console.log(`\n${results.length - failed.length}/${results.length} checks passed.`);
if (failed.length) {
  console.error(`FAILURES:\n${failed.map((f) => f.name).join('\n')}`);
  process.exit(1);
}
