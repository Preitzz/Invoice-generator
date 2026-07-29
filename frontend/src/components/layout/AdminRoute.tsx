import { Navigate, Outlet } from 'react-router-dom';
import { useRole } from '../../hooks/useRole';

/** Redirects non-admins away from admin-only routes (e.g. /audit-log). */
export function AdminRoute() {
  const { isAdmin } = useRole();

  if (!isAdmin) {
    return <Navigate to="/" replace />;
  }

  return <Outlet />;
}
