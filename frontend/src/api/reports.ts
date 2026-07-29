import { get } from './client';
import type { AgingReport, CollectionsReport, CustomerStatement } from '../types/reports';

export const getAgingReport = () => get<AgingReport>('/reports/aging');

export const getCollectionsReport = (start: string, end: string) =>
  get<CollectionsReport>(`/reports/collections?start=${start}&end=${end}`);

export const getCustomerStatement = (customerId: string) =>
  get<CustomerStatement>(`/reports/customer/${customerId}`);
