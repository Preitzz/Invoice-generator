import type { ReactNode } from 'react';
import styles from './ui.module.css';

export function Table({ children }: { children: ReactNode }) {
  return (
    <div className={styles.tableWrap}>
      <table className={styles.table}>{children}</table>
    </div>
  );
}
