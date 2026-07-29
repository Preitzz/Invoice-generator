import { forwardRef, type InputHTMLAttributes } from 'react';
import styles from './ui.module.css';

// eslint-disable-next-line react/display-name
export const Input = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>((props, ref) => (
  <input ref={ref} className={styles.input} {...props} />
));
