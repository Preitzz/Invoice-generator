export interface AuditLogEntryRead {
  id: string;
  entity_type: string;
  entity_id: string;
  action: string;
  actor_id: string | null;
  before_state: Record<string, unknown> | null;
  after_state: Record<string, unknown> | null;
  timestamp: string;
}
