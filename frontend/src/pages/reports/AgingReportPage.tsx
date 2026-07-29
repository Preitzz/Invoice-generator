import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useAgingReport } from '../../hooks/useReports';
import { Spinner } from '../../components/ui/Spinner';
import { ErrorBanner } from '../../components/common/ErrorBanner';
import { EmptyState } from '../../components/ui/EmptyState';
import { Table } from '../../components/ui/Table';
import { Button } from '../../components/ui/Button';
import { formatMoney } from '../../utils/money';
import { formatDate } from '../../utils/date';

export function AgingReportPage() {
  const { data, isLoading, error, refetch } = useAgingReport();
  const [openBuckets, setOpenBuckets] = useState<Record<string, boolean>>({});

  if (isLoading) return <Spinner />;
  if (error) return <ErrorBanner error={error} onRetry={() => refetch()} />;
  if (!data) return null;

  return (
    <div data-testid="aging-report-page">
      <h1>Aging Report</h1>
      {data.buckets.length === 0 ? (
        <EmptyState message="No outstanding invoices." />
      ) : (
        data.buckets.map((bucket) => (
          <section key={bucket.range_label} data-testid={`aging-bucket-${bucket.range_label}`}>
            <Button
              type="button"
              onClick={() => setOpenBuckets((s) => ({ ...s, [bucket.range_label]: !s[bucket.range_label] }))}
              data-testid={`btn-toggle-bucket-${bucket.range_label}`}
            >
              {bucket.range_label} — {formatMoney(bucket.total)} ({bucket.invoices.length})
            </Button>
            {openBuckets[bucket.range_label] && (
              <Table>
                <thead>
                  <tr>
                    <th>Invoice #</th>
                    <th>Due Date</th>
                    <th>Total</th>
                    <th>Paid</th>
                  </tr>
                </thead>
                <tbody>
                  {bucket.invoices.map((inv) => (
                    <tr key={inv.id}>
                      <td>
                        <Link to={`/invoices/${inv.id}`}>{inv.invoice_number ?? 'Draft'}</Link>
                      </td>
                      <td>{formatDate(inv.due_date)}</td>
                      <td>{formatMoney(inv.total_amount)}</td>
                      <td>{formatMoney(inv.amount_paid)}</td>
                    </tr>
                  ))}
                </tbody>
              </Table>
            )}
          </section>
        ))
      )}
    </div>
  );
}
