import type { ReactNode } from 'react';
import styles from './ui.module.css';

interface FormFieldProps {
  name: string;
  label: string;
  error?: string;
  children: ReactNode;
}

export function FormField({ name, label, error, children }: FormFieldProps) {
  return (
    <div className={styles.field} data-testid={`field-${name}`}>
      <label htmlFor={name}>{label}</label>
      {children}
      {error && <span className={styles.fieldError}>{error}</span>}
    </div>
  );
}
