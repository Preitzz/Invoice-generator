import { post } from './client';

export const setReminderKillSwitch = (enabled: boolean) =>
  post<{ enabled: boolean }>('/system/reminders/kill-switch', { enabled });
