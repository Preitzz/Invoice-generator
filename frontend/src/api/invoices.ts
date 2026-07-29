import { get, patch, post } from './client';
import type {
  InvoiceCancelRequest,
  InvoiceCreate,
  InvoiceIssueRequest,
  InvoiceListFilters,
  InvoiceRead,
  InvoiceUpdate,
} from '../types/invoice';

export const listInvoices = (filters: InvoiceListFilters = {}) => {
  const params = new URLSearchParams();
  if (filters.status) params.set('status', filters.status);
  if (filters.customer_id) params.set('customer_id', filters.customer_id);
  const qs = params.toString();
  return get<InvoiceRead[]>(`/invoices${qs ? `?${qs}` : ''}`);
};

export const createInvoice = (payload: InvoiceCreate) => post<InvoiceRead>('/invoices', payload);

export const getInvoice = (id: string) => get<InvoiceRead>(`/invoices/${id}`);

export const updateInvoice = (id: string, payload: InvoiceUpdate) =>
  patch<InvoiceRead>(`/invoices/${id}`, payload);

export const issueInvoice = (id: string, payload: InvoiceIssueRequest = {}) =>
  post<InvoiceRead>(`/invoices/${id}/issue`, payload);

export const cancelInvoice = (id: string, payload: InvoiceCancelRequest) =>
  post<InvoiceRead>(`/invoices/${id}/cancel`, payload);
