import { useQuery } from '@tanstack/react-query';
import { getDashboardSummary } from '../api/dashboard';

export function useDashboardSummary() {
  return useQuery({ queryKey: ['dashboard'], queryFn: getDashboardSummary });
}
