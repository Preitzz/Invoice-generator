import { NavLink, Outlet } from 'react-router-dom';
import { useAuth } from '../../context/useAuth';
import { useRole } from '../../hooks/useRole';
import { Button } from '../ui/Button';
import styles from './AppShell.module.css';

interface NavItem {
  to: string;
  label: string;
  testId: string;
  show: boolean;
}

export function AppShell() {
  const { user, logout } = useAuth();
  const { isAdmin } = useRole();

  const navItems: NavItem[] = [
    { to: '/', label: 'Dashboard', testId: 'nav-dashboard', show: true },
    { to: '/customers', label: 'Customers', testId: 'nav-customers', show: true },
    { to: '/invoices', label: 'Invoices', testId: 'nav-invoices', show: true },
    { to: '/tax-rates', label: 'Tax Rates', testId: 'nav-tax-rates', show: true },
    { to: '/reports/aging', label: 'Reports', testId: 'nav-reports', show: true },
    { to: '/audit-log', label: 'Audit Log', testId: 'nav-audit-log', show: isAdmin },
  ];

  return (
    <div className={styles.shell}>
      <nav className={styles.nav}>
        <span className={styles.brand}>Invoice Reminder</span>
        <div className={styles.navLinks}>
          {navItems
            .filter((item) => item.show)
            .map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === '/'}
                data-testid={item.testId}
                className={({ isActive }) => (isActive ? styles.active : undefined)}
              >
                {item.label}
              </NavLink>
            ))}
        </div>
        <div className={styles.userInfo} data-testid="user-info">
          <span data-testid="user-role">
            {user?.name} ({user?.role})
          </span>
          <Button type="button" onClick={logout} data-testid="btn-logout">
            Log out
          </Button>
        </div>
      </nav>
      <main className={styles.main}>
        <Outlet />
      </main>
    </div>
  );
}
