export type DomainErrorCode =
  | 'overpayment'
  | 'edit_below_payments'
  | 'invoice_not_editable'
  | 'cancel_with_payments'
  | 'customer_has_open_invoices'
  | 'duplicate_payment_warning'
  | 'invalid_state_transition'
  | 'authentication_error'
  | 'authorization_error'
  | 'not_found'
  | 'unknown_error'
  | string;

export class ApiError extends Error {
  status: number;
  code: DomainErrorCode;
  detail: string;

  constructor(status: number, code: DomainErrorCode, detail: string) {
    super(detail);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.detail = detail;
  }
}
