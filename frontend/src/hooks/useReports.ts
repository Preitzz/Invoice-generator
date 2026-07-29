import { useQuery } from '@tanstack/react-query';
import * as reportsApi from '../api/reports';

export function useAgingReport() {
  return useQuery({ queryKey: ['reports', 'aging'], queryFn: reportsApi.getAgingReport });
}

export function useCollectionsReport(start: string | null, end: string | null) {
  return useQuery({
    queryKey: ['reports', 'collections', start, end],
    queryFn: () => reportsApi.getCollectionsReport(start as string, end as string),
    enabled: Boolean(start && end),
  });
}

export function useCustomerStatement(customerId: string | undefined) {
  return useQuery({
    queryKey: ['reports', 'customer', customerId],
    queryFn: () => reportsApi.getCustomerStatement(customerId as string),
    enabled: Boolean(customerId),
  });
}
