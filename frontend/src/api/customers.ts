import { del, get, patch, post } from './client';
import type { CustomerCreate, CustomerRead, CustomerUpdate } from '../types/customer';

export const listCustomers = () => get<CustomerRead[]>('/customers');

export const createCustomer = (payload: CustomerCreate) => post<CustomerRead>('/customers', payload);

export const getCustomer = (id: string) => get<CustomerRead>(`/customers/${id}`);

export const updateCustomer = (id: string, payload: CustomerUpdate) =>
  patch<CustomerRead>(`/customers/${id}`, payload);

export const deactivateCustomer = (id: string) => del<CustomerRead>(`/customers/${id}`);
