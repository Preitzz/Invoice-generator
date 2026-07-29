import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { RoleGate } from '../../src/components/layout/RoleGate';
import { AuthContext, type AuthContextValue } from '../../src/context/AuthContext';
import type { UserRead } from '../../src/types/user';

function renderWithUser(user: UserRead | null, ui: React.ReactNode) {
  const value: AuthContextValue = {
    user,
    token: user ? 'fake-token' : null,
    isAuthenticated: Boolean(user),
    isLoading: false,
    login: async () => {},
    logout: () => {},
  };
  return render(<AuthContext.Provider value={value}>{ui}</AuthContext.Provider>);
}

const adminUser: UserRead = { id: '1', name: 'Admin', email: 'admin@example.com', role: 'admin', is_active: true };
const viewerUser: UserRead = { id: '2', name: 'Viewer', email: 'viewer@example.com', role: 'viewer', is_active: true };

describe('RoleGate', () => {
  it('renders children when the user has an allowed role', () => {
    renderWithUser(
      adminUser,
      <RoleGate roles={['admin']}>
        <button>Admin Action</button>
      </RoleGate>,
    );
    expect(screen.getByText('Admin Action')).toBeInTheDocument();
  });

  it('hides children entirely when the user lacks an allowed role and no disabledVariant is set', () => {
    renderWithUser(
      viewerUser,
      <RoleGate roles={['admin']}>
        <button>Admin Action</button>
      </RoleGate>,
    );
    expect(screen.queryByText('Admin Action')).not.toBeInTheDocument();
  });

  it('renders a fallback when provided and the role does not match', () => {
    renderWithUser(
      viewerUser,
      <RoleGate roles={['admin']} fallback={<span>No access</span>}>
        <button>Admin Action</button>
      </RoleGate>,
    );
    expect(screen.getByText('No access')).toBeInTheDocument();
    expect(screen.queryByText('Admin Action')).not.toBeInTheDocument();
  });

  it('renders children disabled (not hidden) when disabledVariant is set and role does not match', () => {
    renderWithUser(
      viewerUser,
      <RoleGate roles={['admin']} disabledVariant>
        <button>Admin Action</button>
      </RoleGate>,
    );
    const button = screen.getByText('Admin Action');
    expect(button).toBeInTheDocument();
    expect(button).toBeDisabled();
  });

  it('renders children enabled when disabledVariant is set but role matches', () => {
    renderWithUser(
      adminUser,
      <RoleGate roles={['admin']} disabledVariant>
        <button>Admin Action</button>
      </RoleGate>,
    );
    expect(screen.getByText('Admin Action')).not.toBeDisabled();
  });
});
