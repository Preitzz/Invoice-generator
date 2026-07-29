export interface TaxRateRead {
  id: string;
  name: string;
  rate_percent: string;
  effective_from: string;
  effective_to: string | null;
  is_active: boolean;
}

export interface TaxRateCreate {
  name: string;
  rate_percent: string;
  effective_from: string;
}
