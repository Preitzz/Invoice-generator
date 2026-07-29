import type { DomainErrorCode } from '../types/apiError';

const messages: Partial<Record<DomainErrorCode, string>> = {
  overpayment: 'This payment would exceed the amount owed on this invoice.',
  edit_below_payments: 'This edit would reduce the invoice total below the amount already paid.',
  cancel_with_payments: 'This invoice has payments recorded and cannot be cancelled.',
  duplicate_payment_warning: 'A payment of this amount was already recorded recently. Confirm to record it anyway.',
  customer_has_open_invoices: 'This customer has open invoices and cannot be deactivated.',
  invoice_not_editable: 'This invoice can no longer be edited.',
  invalid_state_transition: 'This action is not valid for the invoice in its current state.',
  authentication_error: 'Please log in again.',
  authorization_error: "You don't have permission to do this.",
  not_found: 'The requested item could not be found.',
};

export function friendlyErrorMessage(code: string, detail: string): string {
  return messages[code as DomainErrorCode] ?? detail;
}
