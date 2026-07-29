import type { ButtonHTMLAttributes } from 'react';
import styles from './ui.module.css';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'default' | 'primary' | 'danger';
  title?: string;
}

export function Button({ variant = 'default', className, ...rest }: ButtonProps) {
  const variantClass = variant === 'primary' ? styles.primary : variant === 'danger' ? styles.danger : '';
  return <button className={[styles.button, variantClass, className].filter(Boolean).join(' ')} {...rest} />;
}
