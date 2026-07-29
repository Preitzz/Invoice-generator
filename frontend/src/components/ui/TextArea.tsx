import { forwardRef, type TextareaHTMLAttributes } from 'react';
import styles from './ui.module.css';

// eslint-disable-next-line react/display-name
export const TextArea = forwardRef<HTMLTextAreaElement, TextareaHTMLAttributes<HTMLTextAreaElement>>(
  (props, ref) => <textarea ref={ref} className={styles.textarea} {...props} />,
);
