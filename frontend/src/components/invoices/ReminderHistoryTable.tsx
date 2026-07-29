import { useState } from 'react';
import { Table } from '../ui/Table';
import { EmptyState } from '../ui/EmptyState';
import { Button } from '../ui/Button';
import { RoleGate } from '../layout/RoleGate';
import { ConfirmDialog } from '../ui/ConfirmDialog';
import { Modal } from '../ui/Modal';
import { Input } from '../ui/Input';
import { ErrorBanner } from '../common/ErrorBanner';
import { useCancelReminder, useRescheduleReminder } from '../../hooks/useReminders';
import { useToast } from '../ui/Toast';
import { formatDateTime } from '../../utils/date';
import type { ReminderInstanceRead } from '../../types/reminder';

export function ReminderHistoryTable({ invoiceId, reminders }: { invoiceId: string; reminders: ReminderInstanceRead[] }) {
  const cancelReminder = useCancelReminder(invoiceId);
  const rescheduleReminder = useRescheduleReminder(invoiceId);
  const { showToast } = useToast();
  const [cancellingId, setCancellingId] = useState<string | null>(null);
  const [reschedulingId, setReschedulingId] = useState<string | null>(null);
  const [newTime, setNewTime] = useState('');
  const [actionError, setActionError] = useState<unknown>(null);

  if (reminders.length === 0) return <EmptyState message="No reminders scheduled." />;

  return (
    <div data-testid="reminder-history-table">
      {actionError ? <ErrorBanner error={actionError} /> : null}
      <Table>
        <thead>
          <tr>
            <th>Rule</th>
            <th>Scheduled For</th>
            <th>Status</th>
            <th>Sent At</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {reminders.map((r) => (
            <tr key={r.id} data-testid={`reminder-row-${r.id}`}>
              <td>{r.rule_code}</td>
              <td>{formatDateTime(r.scheduled_for)}</td>
              <td>{r.status}</td>
              <td>{formatDateTime(r.sent_at)}</td>
              <td style={{ display: 'flex', gap: '0.5rem' }}>
                <RoleGate roles={['admin']} disabledVariant>
                  <Button
                    type="button"
                    variant="danger"
                    disabled={r.status !== 'scheduled'}
                    onClick={() => setCancellingId(r.id)}
                    data-testid={`btn-cancel-reminder-${r.id}`}
                  >
                    Cancel
                  </Button>
                </RoleGate>
                <RoleGate roles={['admin']} disabledVariant>
                  <Button
                    type="button"
                    disabled={r.status !== 'scheduled'}
                    onClick={() => {
                      setReschedulingId(r.id);
                      setNewTime('');
                    }}
                    data-testid={`btn-reschedule-reminder-${r.id}`}
                  >
                    Reschedule
                  </Button>
                </RoleGate>
              </td>
            </tr>
          ))}
        </tbody>
      </Table>

      {cancellingId && (
        <ConfirmDialog
          title="Cancel reminder"
          message="Cancel this reminder? It will no longer be sent."
          confirmLabel="Cancel Reminder"
          confirmTestId="confirm-cancel-reminder"
          isPending={cancelReminder.isPending}
          onCancel={() => setCancellingId(null)}
          onConfirm={() => {
            setActionError(null);
            cancelReminder.mutate(
              { reminderId: cancellingId, payload: { reason: 'Cancelled by admin' } },
              {
                onSuccess: () => {
                  setCancellingId(null);
                  showToast('Reminder cancelled');
                },
                onError: (err) => {
                  setActionError(err);
                  setCancellingId(null);
                },
              },
            );
          }}
        />
      )}

      {reschedulingId && (
        <Modal title="Reschedule reminder" onClose={() => setReschedulingId(null)} testId="reschedule-reminder-modal">
          <Input
            type="datetime-local"
            value={newTime}
            onChange={(e) => setNewTime(e.target.value)}
            data-testid="reschedule-reminder-time"
          />
          <div style={{ display: 'flex', gap: '0.5rem', marginTop: '1rem' }}>
            <Button type="button" onClick={() => setReschedulingId(null)}>
              Cancel
            </Button>
            <Button
              type="button"
              variant="primary"
              disabled={!newTime || rescheduleReminder.isPending}
              data-testid="btn-confirm-reschedule-reminder"
              onClick={() => {
                setActionError(null);
                rescheduleReminder.mutate(
                  { reminderId: reschedulingId, payload: { new_scheduled_for: new Date(newTime).toISOString() } },
                  {
                    onSuccess: () => {
                      setReschedulingId(null);
                      showToast('Reminder rescheduled');
                    },
                    onError: (err) => {
                      setActionError(err);
                      setReschedulingId(null);
                    },
                  },
                );
              }}
            >
              Confirm
            </Button>
          </div>
        </Modal>
      )}
    </div>
  );
}
