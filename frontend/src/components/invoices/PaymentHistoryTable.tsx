import { Table } from '../ui/Table';
import { EmptyState } from '../ui/EmptyState';
import { formatMoney } from '../../utils/money';
import { formatDate } from '../../utils/date';
import type { PaymentRead } from '../../types/payment';

export function PaymentHistoryTable({ payments }: { payments: PaymentRead[] }) {
  if (payments.length === 0) return <EmptyState message="No payments recorded yet." />;

  return (
    <Table>
      <thead>
        <tr>
          <th>Amount</th>
          <th>Date</th>
          <th>Method</th>
          <th>Notes</th>
        </tr>
      </thead>
      <tbody>
        {payments.map((p) => (
          <tr key={p.id} data-testid={`payment-row-${p.id}`}>
            <td>{formatMoney(p.amount)}</td>
            <td>{formatDate(p.payment_date)}</td>
            <td>{p.method}</td>
            <td>{p.notes ?? '—'}</td>
          </tr>
        ))}
      </tbody>
    </Table>
  );
}
