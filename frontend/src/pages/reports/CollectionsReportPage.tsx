import { useState } from 'react';
import { useCollectionsReport } from '../../hooks/useReports';
import { Spinner } from '../../components/ui/Spinner';
import { ErrorBanner } from '../../components/common/ErrorBanner';
import { EmptyState } from '../../components/ui/EmptyState';
import { Table } from '../../components/ui/Table';
import { Button } from '../../components/ui/Button';
import { Input } from '../../components/ui/Input';
import { FormField } from '../../components/ui/FormField';
import { formatMoney } from '../../utils/money';
import { formatDate } from '../../utils/date';

export function CollectionsReportPage() {
  const [start, setStart] = useState('');
  const [end, setEnd] = useState('');
  const [submitted, setSubmitted] = useState<{ start: string; end: string } | null>(null);
  const { data, isLoading, error, refetch } = useCollectionsReport(submitted?.start ?? null, submitted?.end ?? null);

  return (
    <div data-testid="collections-report-page">
      <h1>Collections Report</h1>
      <form
        data-testid="collections-report-form"
        onSubmit={(e) => {
          e.preventDefault();
          setSubmitted({ start, end });
        }}
        style={{ display: 'flex', gap: '1rem', alignItems: 'flex-end' }}
      >
        <FormField name="start" label="Start Date">
          <Input type="date" value={start} onChange={(e) => setStart(e.target.value)} data-testid="collections-start" required />
        </FormField>
        <FormField name="end" label="End Date">
          <Input type="date" value={end} onChange={(e) => setEnd(e.target.value)} data-testid="collections-end" required />
        </FormField>
        <Button type="submit" variant="primary" data-testid="btn-run-collections-report">
          Run Report
        </Button>
      </form>

      {isLoading && <Spinner />}
      {error && <ErrorBanner error={error} onRetry={() => refetch()} />}
      {data && (
        <div data-testid="collections-report-results">
          <p>
            {formatDate(data.period_start)} — {formatDate(data.period_end)}: Total {formatMoney(data.total)}
          </p>
          {data.payments.length === 0 ? (
            <EmptyState message="No payments recorded in this period." />
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
      )}
    </div>
  );
}
