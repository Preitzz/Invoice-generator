export type InvoiceStatus = 'draft' | 'issued' | 'partially_paid' | 'paid' | 'cancelled';

export interface LineItemCreate {
  description: string;
  quantity: string;
  unit_price: string;
}

export interface LineItemRead {
  id: string;
  description: string;
  quantity: string;
  unit_price: string;
  tax_rate_snapshot: string | null;
  line_subtotal: string;
  line_tax: string;
  line_total: string;
}

export interface InvoiceRead {
  id: string;
  invoice_number: string | null;
  customer_id: string;
  status: InvoiceStatus;
  issue_date: string | null;
  due_date: string;
  currency: string;
  subtotal: string;
  tax_amount: string;
  total_amount: string;
  amount_paid: string;
  customer_name_snapshot: string | null;
  customer_email_snapshot: string | null;
  customer_address_snapshot: string | null;
  cancelled_at: string | null;
  cancellation_reason: string | null;
  created_at: string;
  updated_at: string;
  is_overdue: boolean;
  line_items: LineItemRead[];
}

export interface InvoiceCreate {
  customer_id: string;
  due_date: string;
  line_items: LineItemCreate[];
}

export interface InvoiceUpdate {
  due_date?: string;
  line_items?: LineItemCreate[];
}

export interface InvoiceIssueRequest {
  note?: string;
}

export interface InvoiceCancelRequest {
  reason: string;
}

export interface InvoiceListFilters {
  status?: InvoiceStatus;
  customer_id?: string;
}
