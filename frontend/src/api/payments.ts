import { get, post } from './client';
import type { PaymentCreate, PaymentCreateResponse, PaymentRead } from '../types/payment';

export const recordPayment = (invoiceId: string, payload: PaymentCreate, confirmDuplicate = false) =>
  post<PaymentCreateResponse>(
    `/invoices/${invoiceId}/payments?confirm_duplicate=${confirmDuplicate ? 'true' : 'false'}`,
    payload,
  );

export const listPayments = (invoiceId: string) => get<PaymentRead[]>(`/invoices/${invoiceId}/payments`);
