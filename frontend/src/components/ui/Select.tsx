import { forwardRef, type SelectHTMLAttributes } from 'react';
import styles from './ui.module.css';

// eslint-disable-next-line react/display-name
export const Select = forwardRef<HTMLSelectElement, SelectHTMLAttributes<HTMLSelectElement>>((props, ref) => (
  <select ref={ref} className={styles.select} {...props} />
));
