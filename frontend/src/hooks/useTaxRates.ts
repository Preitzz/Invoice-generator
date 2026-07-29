import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import * as taxRatesApi from '../api/taxRates';
import type { TaxRateCreate } from '../types/taxRate';

export function useTaxRates() {
  return useQuery({ queryKey: ['taxRates'], queryFn: taxRatesApi.listTaxRates });
}

export function useCreateTaxRate() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: TaxRateCreate) => taxRatesApi.createTaxRate(payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['taxRates'] }),
  });
}
