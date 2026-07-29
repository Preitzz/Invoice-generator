import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import * as paymentsApi from '../api/payments';
import type { PaymentCreate } from '../types/payment';

export function usePayments(invoiceId: string | undefined) {
  return useQuery({
    queryKey: ['invoices', invoiceId, 'payments'],
    queryFn: () => paymentsApi.listPayments(invoiceId as string),
    enabled: Boolean(invoiceId),
  });
}

export function useRecordPayment(invoiceId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ payload, confirmDuplicate }: { payload: PaymentCreate; confirmDuplicate?: boolean }) =>
      paymentsApi.recordPayment(invoiceId, payload, confirmDuplicate),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['invoices', invoiceId] });
      qc.invalidateQueries({ queryKey: ['invoices', invoiceId, 'payments'] });
      qc.invalidateQueries({ queryKey: ['invoices'] });
      qc.invalidateQueries({ queryKey: ['dashboard'] });
    },
  });
}
