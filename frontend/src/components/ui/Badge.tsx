import styles from './ui.module.css';

interface BadgeProps {
  tone?: 'default' | 'success' | 'danger' | 'warning' | 'muted';
  children: React.ReactNode;
  testId?: string;
}

const toneClass: Record<string, string> = {
  success: styles.badgeSuccess,
  danger: styles.badgeDanger,
  warning: styles.badgeWarning,
  muted: styles.badgeMuted,
};

export function Badge({ tone = 'default', children, testId }: BadgeProps) {
  return (
    <span className={[styles.badge, toneClass[tone] ?? ''].filter(Boolean).join(' ')} data-testid={testId}>
      {children}
    </span>
  );
}
