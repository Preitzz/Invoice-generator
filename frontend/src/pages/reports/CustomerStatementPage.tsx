import { useParams, Link } from 'react-router-dom';
import { useCustomerStatement } from '../../hooks/useReports';
import { Spinner } from '../../components/ui/Spinner';
import { ErrorBanner } from '../../components/common/ErrorBanner';
import { EmptyState } from '../../components/ui/EmptyState';
import { Table } from '../../components/ui/Table';
import { formatMoney } from '../../utils/money';
import { formatDate } from '../../utils/date';

export function CustomerStatementPage() {
  const { customerId } = useParams<{ customerId: string }>();
  const { data, isLoading, error, refetch } = useCustomerStatement(customerId);

  if (isLoading) return <Spinner />;
  if (error) return <ErrorBanner error={error} onRetry={() => refetch()} />;
  if (!data) return null;

  return (
    <div data-testid="customer-statement-page">
      <h1>Statement — {data.customer.name}</h1>
      <p>{data.customer.email}</p>

      <h2>Invoices</h2>
      {data.invoices.length === 0 ? (
        <EmptyState message="No invoices for this customer." />
      ) : (
        <Table>
          <thead>
            <tr>
              <th>Invoice #</th>
              <th>Status</th>
              <th>Total</th>
              <th>Paid</th>
              <th>Due Date</th>
            </tr>
          </thead>
          <tbody>
            {data.invoices.map((inv) => (
              <tr key={inv.id}>
                <td>
                  <Link to={`/invoices/${inv.id}`}>{inv.invoice_number ?? 'Draft'}</Link>
                </td>
                <td>{inv.status}</td>
                <td>{formatMoney(inv.total_amount)}</td>
                <td>{formatMoney(inv.amount_paid)}</td>
                <td>{formatDate(inv.due_date)}</td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}

      <h2>Payments</h2>
      {data.payments.length === 0 ? (
        <EmptyState message="No payments recorded." />
      ) : (
        <Table>
          <thead>
            <tr>
              <th>Amount</th>
              <th>Date</th>
              <th>Method</th>
            </tr>
          </thead>
          <tbody>
            {data.payments.map((p) => (
              <tr key={p.id}>
                <td>{formatMoney(p.amount)}</td>
                <td>{formatDate(p.payment_date)}</td>
                <td>{p.method}</td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}
    </div>
  );
}
