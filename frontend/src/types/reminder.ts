export type ReminderInstanceStatus = 'scheduled' | 'sending' | 'sent' | 'cancelled' | 'failed';

export interface ReminderInstanceRead {
  id: string;
  rule_code: string;
  scheduled_for: string;
  status: ReminderInstanceStatus;
  sent_at: string | null;
  cancelled_at: string | null;
  cancellation_reason: string | null;
  attempt_count: number;
}

export interface ReminderRescheduleRequest {
  new_scheduled_for: string;
}

export interface ReminderCancelRequest {
  reason: string;
}
