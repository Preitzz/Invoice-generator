import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useRecordPayment } from '../../hooks/usePayments';
import { ApiError } from '../../types/apiError';
import { Button } from '../ui/Button';
import { FormField } from '../ui/FormField';
import { Select } from '../ui/Select';
import { DecimalInput } from '../common/DecimalInput';
import { Input } from '../ui/Input';
import { ErrorBanner } from '../common/ErrorBanner';
import { ConfirmDialog } from '../ui/ConfirmDialog';
import { useToast } from '../ui/Toast';
import { formatMoney } from '../../utils/money';
import { todayIso } from '../../utils/date';
import type { PaymentCreate } from '../../types/payment';

const schema = z.object({
  amount: z.string().min(1, 'Amount is required').refine((v) => Number(v) > 0, 'Amount must be greater than 0'),
  payment_date: z.string().min(1, 'Payment date is required'),
  method: z.enum(['cash', 'bank_transfer', 'upi', 'cheque']),
  notes: z.string().optional(),
});

type FormValues = z.infer<typeof schema>;

interface PaymentFormProps {
  invoiceId: string;
  maxAllowed: string;
}

export function PaymentForm({ invoiceId, maxAllowed }: PaymentFormProps) {
  const recordPayment = useRecordPayment(invoiceId);
  const { showToast } = useToast();
  const [error, setError] = useState<unknown>(null);
  const [pendingPayload, setPendingPayload] = useState<PaymentCreate | null>(null);

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { amount: '', payment_date: todayIso(), method: 'cash', notes: '' },
  });

  const submit = (payload: PaymentCreate, confirmDuplicate: boolean) => {
    setError(null);
    recordPayment.mutate(
      { payload, confirmDuplicate },
      {
        onSuccess: () => {
          setPendingPayload(null);
          reset({ amount: '', payment_date: todayIso(), method: 'cash', notes: '' });
          showToast('Payment recorded');
        },
        onError: (err) => {
          if (err instanceof ApiError && err.status === 409 && err.code === 'duplicate_payment_warning') {
            setPendingPayload(payload);
          } else {
            setError(err);
          }
        },
      },
    );
  };

  const onSubmit = (values: FormValues) => {
    const payload: PaymentCreate = {
      amount: values.amount,
      payment_date: values.payment_date,
      method: values.method,
      notes: values.notes || undefined,
    };
    submit(payload, false);
  };

  return (
    <div data-testid="payment-form-wrap">
      {error ? <ErrorBanner error={error} /> : null}
      <p>Max allowed payment: {formatMoney(maxAllowed)}</p>
      <form onSubmit={handleSubmit(onSubmit)} data-testid="payment-form">
        <FormField name="payment-form-amount" label="Amount" error={errors.amount?.message}>
          <DecimalInput {...register('amount')} data-testid="payment-form-amount" />
        </FormField>
        <FormField name="payment-form-date" label="Payment Date" error={errors.payment_date?.message}>
          <Input type="date" {...register('payment_date')} data-testid="payment-form-date" />
        </FormField>
        <FormField name="payment-form-method" label="Method">
          <Select {...register('method')} data-testid="payment-form-method">
            <option value="cash">Cash</option>
            <option value="bank_transfer">Bank Transfer</option>
            <option value="upi">UPI</option>
            <option value="cheque">Cheque</option>
          </Select>
        </FormField>
        <FormField name="payment-form-notes" label="Notes">
          <Input {...register('notes')} data-testid="payment-form-notes" />
        </FormField>
        <Button type="submit" variant="primary" disabled={recordPayment.isPending} data-testid="payment-form-submit">
          {recordPayment.isPending ? 'Recording…' : 'Record Payment'}
        </Button>
      </form>

      {pendingPayload && (
        <ConfirmDialog
          title="Possible duplicate payment"
          message="A payment of this amount was already recorded on this invoice within the last hour. Record it anyway?"
          confirmLabel="Record anyway"
          confirmTestId="duplicate-payment-confirm"
          isPending={recordPayment.isPending}
          onCancel={() => setPendingPayload(null)}
          onConfirm={() => submit(pendingPayload, true)}
        />
      )}
    </div>
  );
}
