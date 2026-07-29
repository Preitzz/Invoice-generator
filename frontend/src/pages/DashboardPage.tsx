import { Link } from 'react-router-dom';
import { useDashboardSummary } from '../hooks/useDashboard';
import { Spinner } from '../components/ui/Spinner';
import { ErrorBanner } from '../components/common/ErrorBanner';
import { EmptyState } from '../components/ui/EmptyState';
import { Table } from '../components/ui/Table';
import { formatMoney } from '../utils/money';
import { formatDate } from '../utils/date';
import styles from './DashboardPage.module.css';

export function DashboardPage() {
  const { data, isLoading, error, refetch } = useDashboardSummary();

  if (isLoading) return <Spinner />;
  if (error) return <ErrorBanner error={error} onRetry={() => refetch()} />;
  if (!data) return null;

  return (
    <div data-testid="dashboard-page">
      <h1>Dashboard</h1>
      <div className={styles.stats}>
        <div className={styles.stat} data-testid="stat-total-outstanding">
          <span className={styles.statLabel}>Total Outstanding</span>
          <span className={styles.statValue}>{formatMoney(data.total_outstanding)}</span>
        </div>
        <div className={styles.stat} data-testid="stat-overdue-count">
          <span className={styles.statLabel}>Overdue Invoices</span>
          <span className={styles.statValue}>{data.overdue_count}</span>
        </div>
      </div>

      <h2>Upcoming Due</h2>
      {data.upcoming_due.length === 0 ? (
        <EmptyState message="No invoices due soon." />
      ) : (
        <Table>
          <thead>
            <tr>
              <th>Invoice</th>
              <th>Due Date</th>
              <th>Total</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {data.upcoming_due.map((inv) => (
              <tr key={inv.id} data-testid={`invoice-row-${inv.id}`}>
                <td>
                  <Link to={`/invoices/${inv.id}`}>{inv.invoice_number ?? 'Draft'}</Link>
                </td>
                <td>{formatDate(inv.due_date)}</td>
                <td>{formatMoney(inv.total_amount)}</td>
                <td>{inv.status}</td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}

      <h2>Recent Payments</h2>
      {data.recent_payments.length === 0 ? (
        <EmptyState message="No recent payments." />
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
            {data.recent_payments.map((p) => (
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
