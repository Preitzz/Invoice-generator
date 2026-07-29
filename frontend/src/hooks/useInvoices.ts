import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import * as invoicesApi from '../api/invoices';
import type {
  InvoiceCancelRequest,
  InvoiceCreate,
  InvoiceIssueRequest,
  InvoiceListFilters,
  InvoiceUpdate,
} from '../types/invoice';

export function useInvoices(filters: InvoiceListFilters = {}) {
  return useQuery({
    queryKey: ['invoices', filters],
    queryFn: () => invoicesApi.listInvoices(filters),
  });
}

export function useInvoice(id: string | undefined) {
  return useQuery({
    queryKey: ['invoices', id],
    queryFn: () => invoicesApi.getInvoice(id as string),
    enabled: Boolean(id),
  });
}

function invalidateInvoice(qc: ReturnType<typeof useQueryClient>, id: string) {
  qc.invalidateQueries({ queryKey: ['invoices'] });
  qc.invalidateQueries({ queryKey: ['invoices', id] });
  qc.invalidateQueries({ queryKey: ['dashboard'] });
}

export function useCreateInvoice() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: InvoiceCreate) => invoicesApi.createInvoice(payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['invoices'] });
      qc.invalidateQueries({ queryKey: ['dashboard'] });
    },
  });
}

export function useUpdateInvoice(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: InvoiceUpdate) => invoicesApi.updateInvoice(id, payload),
    onSuccess: () => invalidateInvoice(qc, id),
  });
}

export function useIssueInvoice(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: InvoiceIssueRequest = {}) => invoicesApi.issueInvoice(id, payload),
    onSuccess: () => invalidateInvoice(qc, id),
  });
}

export function useCancelInvoice(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: InvoiceCancelRequest) => invoicesApi.cancelInvoice(id, payload),
    onSuccess: () => {
      invalidateInvoice(qc, id);
      qc.invalidateQueries({ queryKey: ['invoices', id, 'reminders'] });
    },
  });
}
