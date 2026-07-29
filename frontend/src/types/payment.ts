export type PaymentMethod = 'cash' | 'bank_transfer' | 'upi' | 'cheque';

export interface PaymentRead {
  id: string;
  invoice_id: string;
  amount: string;
  payment_date: string;
  method: PaymentMethod;
  notes: string | null;
  recorded_by: string;
  created_at: string;
}

export interface PaymentCreate {
  amount: string;
  payment_date: string;
  method: PaymentMethod;
  notes?: string;
  confirm_duplicate?: boolean;
}

export interface PaymentCreateResponse {
  payment: PaymentRead;
  duplicate_warning: boolean;
  duplicate_of: string | null;
}
