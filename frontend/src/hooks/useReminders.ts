import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import * as remindersApi from '../api/reminders';
import type { ReminderCancelRequest, ReminderRescheduleRequest } from '../types/reminder';

export function useReminders(invoiceId: string | undefined) {
  return useQuery({
    queryKey: ['invoices', invoiceId, 'reminders'],
    queryFn: () => remindersApi.listReminders(invoiceId as string),
    enabled: Boolean(invoiceId),
  });
}

export function useCancelReminder(invoiceId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ reminderId, payload }: { reminderId: string; payload: ReminderCancelRequest }) =>
      remindersApi.cancelReminder(invoiceId, reminderId, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['invoices', invoiceId, 'reminders'] }),
  });
}

export function useRescheduleReminder(invoiceId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ reminderId, payload }: { reminderId: string; payload: ReminderRescheduleRequest }) =>
      remindersApi.rescheduleReminder(invoiceId, reminderId, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['invoices', invoiceId, 'reminders'] }),
  });
}
