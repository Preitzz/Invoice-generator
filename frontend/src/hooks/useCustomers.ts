import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import * as customersApi from '../api/customers';
import type { CustomerCreate, CustomerUpdate } from '../types/customer';

export function useCustomers() {
  return useQuery({ queryKey: ['customers'], queryFn: customersApi.listCustomers });
}

export function useCustomer(id: string | undefined) {
  return useQuery({
    queryKey: ['customers', id],
    queryFn: () => customersApi.getCustomer(id as string),
    enabled: Boolean(id),
  });
}

export function useCreateCustomer() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: CustomerCreate) => customersApi.createCustomer(payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['customers'] });
    },
  });
}

export function useUpdateCustomer(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: CustomerUpdate) => customersApi.updateCustomer(id, payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['customers'] });
      qc.invalidateQueries({ queryKey: ['customers', id] });
    },
  });
}

export function useDeactivateCustomer(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => customersApi.deactivateCustomer(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['customers'] });
      qc.invalidateQueries({ queryKey: ['customers', id] });
    },
  });
}
