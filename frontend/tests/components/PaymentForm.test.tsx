import { describe, expect, it, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { PaymentForm } from '../../src/components/invoices/PaymentForm';
import { ToastProvider } from '../../src/components/ui/Toast';
import { ApiError } from '../../src/types/apiError';
import * as paymentsApi from '../../src/api/payments';

vi.mock('../../src/api/payments');

function renderPaymentForm() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <ToastProvider>
        <PaymentForm invoiceId="invoice-1" maxAllowed="1000.00" />
      </ToastProvider>
    </QueryClientProvider>,
  );
}

describe('PaymentForm duplicate-confirm branch', () => {
  beforeEach(() => {
    vi.mocked(paymentsApi.recordPayment).mockReset();
  });

  it('opens a duplicate-confirm dialog on a 409 duplicate_payment_warning and resubmits with confirm_duplicate on confirm', async () => {
    const user = userEvent.setup();

    vi.mocked(paymentsApi.recordPayment).mockImplementationOnce(() => {
      throw new ApiError(409, 'duplicate_payment_warning', 'A payment of this amount was already recorded recently.');
    });
    vi.mocked(paymentsApi.recordPayment).mockResolvedValueOnce({
      payment: {
        id: 'p1',
        invoice_id: 'invoice-1',
        amount: '100.00',
        payment_date: '2026-07-29',
        method: 'cash',
        notes: null,
        recorded_by: 'u1',
        created_at: '2026-07-29T00:00:00Z',
      },
      duplicate_warning: true,
      duplicate_of: 'p0',
    });

    renderPaymentForm();

    await user.type(screen.getByTestId('payment-form-amount'), '100.00');
    fireEvent.change(screen.getByTestId('payment-form-date'), { target: { value: '2026-07-29' } });
    await user.click(screen.getByTestId('payment-form-submit'));

    await waitFor(() => expect(screen.getByTestId('duplicate-payment-confirm')).toBeInTheDocument());

    await user.click(screen.getByTestId('duplicate-payment-confirm'));

    await waitFor(() => expect(paymentsApi.recordPayment).toHaveBeenCalledTimes(2));
    expect(paymentsApi.recordPayment).toHaveBeenLastCalledWith(
      'invoice-1',
      expect.objectContaining({ amount: '100' }),
      true,
    );
  });

  it('surfaces a non-duplicate error inline without opening the confirm dialog', async () => {
    const user = userEvent.setup();
    vi.mocked(paymentsApi.recordPayment).mockImplementationOnce(() => {
      throw new ApiError(400, 'overpayment', 'This payment would exceed the amount owed on this invoice.');
    });

    renderPaymentForm();
    await user.type(screen.getByTestId('payment-form-amount'), '99999.00');
    fireEvent.change(screen.getByTestId('payment-form-date'), { target: { value: '2026-07-29' } });
    await user.click(screen.getByTestId('payment-form-submit'));

    await waitFor(() => expect(screen.getByTestId('error-banner')).toBeInTheDocument());
    expect(screen.queryByTestId('duplicate-payment-confirm')).not.toBeInTheDocument();
  });
});
