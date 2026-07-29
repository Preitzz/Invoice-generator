import type { InvoiceRead } from './invoice';
import type { PaymentRead } from './payment';

export interface DashboardSummary {
  total_outstanding: string;
  overdue_count: number;
  upcoming_due: InvoiceRead[];
  recent_payments: PaymentRead[];
}
