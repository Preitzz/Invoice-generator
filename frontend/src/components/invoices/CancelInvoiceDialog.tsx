import { useState } from 'react';
import { Modal, modalStyles } from '../ui/Modal';
import { Button } from '../ui/Button';
import { TextArea } from '../ui/TextArea';
import { FormField } from '../ui/FormField';
import { ErrorBanner } from '../common/ErrorBanner';

interface CancelInvoiceDialogProps {
  onConfirm: (reason: string) => void;
  onClose: () => void;
  isPending?: boolean;
  error?: unknown;
}

export function CancelInvoiceDialog({ onConfirm, onClose, isPending, error }: CancelInvoiceDialogProps) {
  const [reason, setReason] = useState('');

  return (
    <Modal title="Cancel invoice" onClose={onClose} testId="cancel-invoice-modal">
      {error ? <ErrorBanner error={error} /> : null}
      <FormField name="cancel-reason" label="Reason for cancellation">
        <TextArea
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          data-testid="cancel-invoice-reason"
        />
      </FormField>
      <div className={modalStyles.modalActions}>
        <Button type="button" onClick={onClose}>
          Back
        </Button>
        <Button
          type="button"
          variant="danger"
          disabled={!reason.trim() || isPending}
          onClick={() => onConfirm(reason.trim())}
          data-testid="confirm-cancel-invoice"
        >
          Cancel Invoice
        </Button>
      </div>
    </Modal>
  );
}
