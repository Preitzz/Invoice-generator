import { useAuth } from '../context/useAuth';
import type { UserRole } from '../types/user';

export function useRole() {
  const { user } = useAuth();
  const role: UserRole | null = user?.role ?? null;
  return {
    role,
    isAdmin: role === 'admin',
    isStaff: role === 'admin' || role === 'finance_staff',
    isViewer: role === 'viewer',
  };
}
