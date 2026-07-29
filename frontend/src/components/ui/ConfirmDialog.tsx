import { Modal, modalStyles } from './Modal';
import { Button } from './Button';

interface ConfirmDialogProps {
  title: string;
  message: string;
  confirmLabel?: string;
  onConfirm: () => void;
  onCancel: () => void;
  confirmTestId?: string;
  isPending?: boolean;
}

export function ConfirmDialog({
  title,
  message,
  confirmLabel = 'Confirm',
  onConfirm,
  onCancel,
  confirmTestId,
  isPending,
}: ConfirmDialogProps) {
  return (
    <Modal title={title} onClose={onCancel} testId="confirm-dialog">
      <p>{message}</p>
      <div className={modalStyles.modalActions}>
        <Button onClick={onCancel} type="button">
          Cancel
        </Button>
        <Button variant="primary" onClick={onConfirm} disabled={isPending} data-testid={confirmTestId} type="button">
          {confirmLabel}
        </Button>
      </div>
    </Modal>
  );
}
