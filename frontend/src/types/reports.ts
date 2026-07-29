import type { CustomerRead } from './customer';
import type { InvoiceRead } from './invoice';
import type { PaymentRead } from './payment';

export interface AgingBucket {
  range_label: string;
  invoices: InvoiceRead[];
  total: string;
}

export interface AgingReport {
  buckets: AgingBucket[];
}

export interface CollectionsReport {
  period_start: string;
  period_end: string;
  payments: PaymentRead[];
  total: string;
}

export interface CustomerStatement {
  customer: CustomerRead;
  invoices: InvoiceRead[];
  payments: PaymentRead[];
}
