import { useSearchParams, Link } from 'react-router-dom';
import { useInvoices } from '../../hooks/useInvoices';
import { useCustomers } from '../../hooks/useCustomers';
import { useRole } from '../../hooks/useRole';
import { Spinner } from '../../components/ui/Spinner';
import { ErrorBanner } from '../../components/common/ErrorBanner';
import { EmptyState } from '../../components/ui/EmptyState';
import { Table } from '../../components/ui/Table';
import { Button } from '../../components/ui/Button';
import { Select } from '../../components/ui/Select';
import { InvoiceStatusBadge } from '../../components/invoices/InvoiceStatusBadge';
import { formatMoney } from '../../utils/money';
import { formatDate } from '../../utils/date';
import type { InvoiceStatus } from '../../types/invoice';

const STATUSES: InvoiceStatus[] = ['draft', 'issued', 'partially_paid', 'paid', 'cancelled'];

export function InvoiceListPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const status = (searchParams.get('status') as InvoiceStatus | null) ?? undefined;
  const customerId = searchParams.get('customer_id') ?? undefined;
  const { isStaff } = useRole();
  const { data: customers } = useCustomers();
  const { data, isLoading, error, refetch } = useInvoices({ status, customer_id: customerId });

  const updateParam = (key: string, value: string) => {
    const next = new URLSearchParams(searchParams);
    if (value) next.set(key, value);
    else next.delete(key);
    setSearchParams(next);
  };

  return (
    <div data-testid="invoice-list-page">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h1>Invoices</h1>
        {isStaff && (
          <Link to="/invoices/new">
            <Button variant="primary" data-testid="btn-new-invoice">
              New Invoice
            </Button>
          </Link>
        )}
      </div>

      <div style={{ display: 'flex', gap: '1rem', margin: '1rem 0' }}>
        <Select
          value={status ?? ''}
          onChange={(e) => updateParam('status', e.target.value)}
          data-testid="filter-status"
        >
          <option value="">All statuses</option>
          {STATUSES.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </Select>
        <Select
          value={customerId ?? ''}
          onChange={(e) => updateParam('customer_id', e.target.value)}
          data-testid="filter-customer"
        >
          <option value="">All customers</option>
          {customers?.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </Select>
      </div>

      {isLoading ? (
        <Spinner />
      ) : error ? (
        <ErrorBanner error={error} onRetry={() => refetch()} />
      ) : data && data.length === 0 ? (
        <EmptyState message="No invoices match these filters." />
      ) : (
        <Table>
          <thead>
            <tr>
              <th>Invoice #</th>
              <th>Status</th>
              <th>Overdue</th>
              <th>Total</th>
              <th>Paid</th>
              <th>Due Date</th>
            </tr>
          </thead>
          <tbody>
            {data?.map((inv) => (
              <tr key={inv.id} data-testid={`invoice-row-${inv.id}`}>
                <td>
                  <Link to={`/invoices/${inv.id}`}>{inv.invoice_number ?? 'Draft'}</Link>
                </td>
                <td>
                  <InvoiceStatusBadge status={inv.status} />
                </td>
                <td>{inv.is_overdue ? 'Overdue' : '—'}</td>
                <td data-testid="invoice-total">{formatMoney(inv.total_amount)}</td>
                <td>{formatMoney(inv.amount_paid)}</td>
                <td>{formatDate(inv.due_date)}</td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}
    </div>
  );
}
