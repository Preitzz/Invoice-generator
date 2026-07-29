import type { ReactNode } from 'react';
import styles from './ui.module.css';

interface ModalProps {
  title: string;
  onClose: () => void;
  children: ReactNode;
  testId?: string;
}

export function Modal({ title, onClose, children, testId }: ModalProps) {
  return (
    <div className={styles.modalOverlay} onClick={onClose} data-testid={testId}>
      <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
        <h3>{title}</h3>
        {children}
      </div>
    </div>
  );
}

export { styles as modalStyles };
