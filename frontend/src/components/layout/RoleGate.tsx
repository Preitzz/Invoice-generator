import type { ReactNode } from 'react';
import { useAuth } from '../../context/useAuth';
import type { UserRole } from '../../types/user';

interface RoleGateProps {
  roles: UserRole[];
  children: ReactNode;
  /** If true, renders children disabled (via a wrapping span with aria-disabled) instead of hiding them. */
  disabledVariant?: boolean;
  fallback?: ReactNode;
}

export function RoleGate({ roles, children, disabledVariant = false, fallback = null }: RoleGateProps) {
  const { user } = useAuth();
  const allowed = Boolean(user && roles.includes(user.role));

  if (allowed) return <>{children}</>;

  if (disabledVariant) {
    return (
      <span title="Admin only" aria-disabled="true" style={{ display: 'inline-block', cursor: 'not-allowed', opacity: 0.5 }}>
        <fieldset disabled style={{ border: 'none', padding: 0, margin: 0 }}>
          {children}
        </fieldset>
      </span>
    );
  }

  return <>{fallback}</>;
}
