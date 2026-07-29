import { createBrowserRouter } from 'react-router-dom';
import { AppShell } from './components/layout/AppShell';
import { ProtectedRoute } from './components/layout/ProtectedRoute';
import { AdminRoute } from './components/layout/AdminRoute';
import { LoginPage } from './pages/LoginPage';
import { DashboardPage } from './pages/DashboardPage';
import { NotFoundPage } from './pages/NotFoundPage';
import { CustomerListPage } from './pages/customers/CustomerListPage';
import { CustomerDetailPage } from './pages/customers/CustomerDetailPage';
import { InvoiceListPage } from './pages/invoices/InvoiceListPage';
import { InvoiceCreatePage } from './pages/invoices/InvoiceCreatePage';
import { InvoiceDetailPage } from './pages/invoices/InvoiceDetailPage';
import { InvoiceEditPage } from './pages/invoices/InvoiceEditPage';
import { TaxRatePage } from './pages/taxRates/TaxRatePage';
import { AgingReportPage } from './pages/reports/AgingReportPage';
import { CollectionsReportPage } from './pages/reports/CollectionsReportPage';
import { CustomerStatementPage } from './pages/reports/CustomerStatementPage';
import { AuditLogPage } from './pages/audit/AuditLogPage';

export const router = createBrowserRouter([
  { path: '/login', element: <LoginPage /> },
  {
    element: <ProtectedRoute />,
    children: [
      {
        element: <AppShell />,
        children: [
          { path: '/', element: <DashboardPage /> },
          { path: '/customers', element: <CustomerListPage /> },
          { path: '/customers/:id', element: <CustomerDetailPage /> },
          { path: '/invoices', element: <InvoiceListPage /> },
          { path: '/invoices/new', element: <InvoiceCreatePage /> },
          { path: '/invoices/:id', element: <InvoiceDetailPage /> },
          { path: '/invoices/:id/edit', element: <InvoiceEditPage /> },
          { path: '/tax-rates', element: <TaxRatePage /> },
          { path: '/reports/aging', element: <AgingReportPage /> },
          { path: '/reports/collections', element: <CollectionsReportPage /> },
          { path: '/reports/customer/:customerId', element: <CustomerStatementPage /> },
          {
            element: <AdminRoute />,
            children: [{ path: '/audit-log', element: <AuditLogPage /> }],
          },
          { path: '*', element: <NotFoundPage /> },
        ],
      },
    ],
  },
]);
