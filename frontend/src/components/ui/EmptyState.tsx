import styles from './ui.module.css';

export function EmptyState({ message }: { message: string }) {
  return (
    <div className={styles.emptyState} data-testid="empty-state">
      {message}
    </div>
  );
}
