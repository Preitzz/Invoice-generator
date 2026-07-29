import { Badge } from '../ui/Badge';
import type { InvoiceStatus } from '../../types/invoice';

const toneByStatus: Record<InvoiceStatus, 'default' | 'success' | 'danger' | 'warning' | 'muted'> = {
  draft: 'muted',
  issued: 'default',
  partially_paid: 'warning',
  paid: 'success',
  cancelled: 'danger',
};

const labelByStatus: Record<InvoiceStatus, string> = {
  draft: 'Draft',
  issued: 'Issued',
  partially_paid: 'Partially Paid',
  paid: 'Paid',
  cancelled: 'Cancelled',
};

export function InvoiceStatusBadge({ status }: { status: InvoiceStatus }) {
  return (
    <Badge tone={toneByStatus[status]} testId="invoice-status-badge">
      {labelByStatus[status]}
    </Badge>
  );
}
