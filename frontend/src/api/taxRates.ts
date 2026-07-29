import { get, post } from './client';
import type { TaxRateCreate, TaxRateRead } from '../types/taxRate';

export const listTaxRates = () => get<TaxRateRead[]>('/tax-rates');

export const createTaxRate = (payload: TaxRateCreate) => post<TaxRateRead>('/tax-rates', payload);
