import { useQuery } from '@tanstack/react-query';
import { listAuditLog, type AuditLogFilters } from '../api/auditLog';

export function useAuditLog(filters: AuditLogFilters = {}) {
  return useQuery({
    queryKey: ['auditLog', filters],
    queryFn: () => listAuditLog(filters),
  });
}
