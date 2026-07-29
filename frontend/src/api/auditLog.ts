import { get } from './client';
import type { AuditLogEntryRead } from '../types/audit';

export interface AuditLogFilters {
  entity_type?: string;
  entity_id?: string;
}

export const listAuditLog = (filters: AuditLogFilters = {}) => {
  const params = new URLSearchParams();
  if (filters.entity_type) params.set('entity_type', filters.entity_type);
  if (filters.entity_id) params.set('entity_id', filters.entity_id);
  const qs = params.toString();
  return get<AuditLogEntryRead[]>(`/audit-log${qs ? `?${qs}` : ''}`);
};
