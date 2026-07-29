import { get, post } from './client';
import type {
  ReminderCancelRequest,
  ReminderInstanceRead,
  ReminderRescheduleRequest,
} from '../types/reminder';

export const listReminders = (invoiceId: string) =>
  get<ReminderInstanceRead[]>(`/invoices/${invoiceId}/reminders`);

export const cancelReminder = (invoiceId: string, reminderId: string, payload: ReminderCancelRequest) =>
  post<ReminderInstanceRead>(`/invoices/${invoiceId}/reminders/${reminderId}/cancel`, payload);

export const rescheduleReminder = (
  invoiceId: string,
  reminderId: string,
  payload: ReminderRescheduleRequest,
) => post<ReminderInstanceRead>(`/invoices/${invoiceId}/reminders/${reminderId}/reschedule`, payload);
