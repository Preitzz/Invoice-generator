import { Fragment, useState } from 'react';
import { useAuditLog } from '../../hooks/useAuditLog';
import { Spinner } from '../../components/ui/Spinner';
import { ErrorBanner } from '../../components/common/ErrorBanner';
import { EmptyState } from '../../components/ui/EmptyState';
import { Table } from '../../components/ui/Table';
import { Input } from '../../components/ui/Input';
import { FormField } from '../../components/ui/FormField';
import { formatDateTime } from '../../utils/date';

export function AuditLogPage() {
  const [entityType, setEntityType] = useState('');
  const [entityId, setEntityId] = useState('');
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const { data, isLoading, error, refetch } = useAuditLog({
    entity_type: entityType || undefined,
    entity_id: entityId || undefined,
  });

  return (
    <div data-testid="audit-log-page">
      <h1>Audit Log</h1>
      <div style={{ display: 'flex', gap: '1rem' }}>
        <FormField name="entity_type" label="Entity Type">
          <Input value={entityType} onChange={(e) => setEntityType(e.target.value)} data-testid="audit-filter-entity-type" />
        </FormField>
        <FormField name="entity_id" label="Entity ID">
          <Input value={entityId} onChange={(e) => setEntityId(e.target.value)} data-testid="audit-filter-entity-id" />
        </FormField>
      </div>

      {isLoading && <Spinner />}
      {error && <ErrorBanner error={error} onRetry={() => refetch()} />}
      {data && data.length === 0 && <EmptyState message="No audit log entries match these filters." />}
      {data && data.length > 0 && (
        <Table>
          <thead>
            <tr>
              <th>Timestamp</th>
              <th>Entity Type</th>
              <th>Entity ID</th>
              <th>Action</th>
              <th>Actor</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {data.map((entry) => (
              <Fragment key={entry.id}>
                <tr data-testid={`audit-row-${entry.id}`}>
                  <td>{formatDateTime(entry.timestamp)}</td>
                  <td>{entry.entity_type}</td>
                  <td>{entry.entity_id}</td>
                  <td>{entry.action}</td>
                  <td>{entry.actor_id ?? '—'}</td>
                  <td>
                    <button
                      type="button"
                      onClick={() => setExpandedId(expandedId === entry.id ? null : entry.id)}
                      data-testid={`btn-expand-audit-${entry.id}`}
                    >
                      {expandedId === entry.id ? 'Hide' : 'Details'}
                    </button>
                  </td>
                </tr>
                {expandedId === entry.id && (
                  <tr>
                    <td colSpan={6}>
                      <div style={{ display: 'flex', gap: '1rem' }}>
                        <div>
                          <h4>Before</h4>
                          <pre data-testid={`audit-before-${entry.id}`}>
                            {JSON.stringify(entry.before_state, null, 2)}
                          </pre>
                        </div>
                        <div>
                          <h4>After</h4>
                          <pre data-testid={`audit-after-${entry.id}`}>
                            {JSON.stringify(entry.after_state, null, 2)}
                          </pre>
                        </div>
                      </div>
                    </td>
                  </tr>
                )}
              </Fragment>
            ))}
          </tbody>
        </Table>
      )}
    </div>
  );
}
