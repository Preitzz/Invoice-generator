import { useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { useInvoice, useIssueInvoice, useCancelInvoice } from '../../hooks/useInvoices';
import { usePayments } from '../../hooks/usePayments';
import { useReminders } from '../../hooks/useReminders';
import { useRole } from '../../hooks/useRole';
import { Spinner } from '../../components/ui/Spinner';
import { ErrorBanner } from '../../components/common/ErrorBanner';
import { Button } from '../../components/ui/Button';
import { InvoiceStatusBadge } from '../../components/invoices/InvoiceStatusBadge';
import { PaymentHistoryTable } from '../../components/invoices/PaymentHistoryTable';
import { PaymentForm } from '../../components/invoices/PaymentForm';
import { ReminderHistoryTable } from '../../components/invoices/ReminderHistoryTable';
import { CancelInvoiceDialog } from '../../components/invoices/CancelInvoiceDialog';
import { useToast } from '../../components/ui/Toast';
import { formatMoney } from '../../utils/money';
import { formatDate } from '../../utils/date';
import { Table } from '../../components/ui/Table';

export function InvoiceDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { data: invoice, isLoading, error, refetch } = useInvoice(id);
  const { data: payments, isLoading: paymentsLoading } = usePayments(id);
  const { data: reminders, isLoading: remindersLoading } = useReminders(id);
  const { isStaff } = useRole();
  const issueInvoice = useIssueInvoice(id ?? '');
  const cancelInvoice = useCancelInvoice(id ?? '');
  const { showToast } = useToast();

  const [showCancelDialog, setShowCancelDialog] = useState(false);
  const [issueError, setIssueError] = useState<unknown>(null);
  const [cancelError, setCancelError] = useState<unknown>(null);

  if (isLoading) return <Spinner />;
  if (error) return <ErrorBanner error={error} onRetry={() => refetch()} />;
  if (!invoice) return null;

  const canEdit = isStaff && !['paid', 'cancelled'].includes(invoice.status);
  const canIssue = isStaff && invoice.status === 'draft';
  const canCancelState = ['draft', 'issued', 'partially_paid'].includes(invoice.status);
  const hasPayments = Number(invoice.amount_paid) > 0;
  const canRecordPayment = isStaff && ['issued', 'partially_paid'].includes(invoice.status);
  const maxAllowedPayment = (Number(invoice.total_amount) - Number(invoice.amount_paid)).toFixed(2);

  return (
    <div data-testid="invoice-detail-page">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.5rem' }}>
        <h1 data-testid="invoice-header">{invoice.invoice_number ?? 'Draft Invoice'}</h1>
        <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
          <InvoiceStatusBadge status={invoice.status} />
          {invoice.is_overdue && <span data-testid="invoice-overdue-flag">Overdue</span>}
        </div>
      </div>

      <div style={{ display: 'flex', gap: '0.5rem', margin: '1rem 0' }}>
        {isStaff && (
          <Button
            type="button"
            disabled={!canEdit}
            title={!canEdit ? 'This invoice can no longer be edited.' : undefined}
            onClick={() => navigate(`/invoices/${invoice.id}/edit`)}
            data-testid="btn-edit-invoice"
          >
            Edit
          </Button>
        )}
        {isStaff && canIssue && (
          <Button
            type="button"
            variant="primary"
            disabled={issueInvoice.isPending}
            onClick={() => {
              setIssueError(null);
              issueInvoice.mutate(
                {},
                {
                  onSuccess: () => showToast('Invoice issued'),
                  onError: (err) => setIssueError(err),
                },
              );
            }}
            data-testid="btn-issue-invoice"
          >
            Issue
          </Button>
        )}
        {isStaff && canCancelState && (
          <Button
            type="button"
            variant="danger"
            disabled={hasPayments}
            title={hasPayments ? 'This invoice has payments recorded and cannot be cancelled.' : undefined}
            onClick={() => setShowCancelDialog(true)}
            data-testid="btn-cancel-invoice"
          >
            Cancel
          </Button>
        )}
      </div>

      {issueError ? <ErrorBanner error={issueError} /> : null}
      {cancelError && !showCancelDialog ? <ErrorBanner error={cancelError} /> : null}

      <section>
        <h2>Customer</h2>
        <p>{invoice.customer_name_snapshot ?? '—'}</p>
        <p>{invoice.customer_email_snapshot ?? '—'}</p>
        <p>{invoice.customer_address_snapshot ?? '—'}</p>
        <Link to={`/customers/${invoice.customer_id}`}>View customer</Link>
      </section>

      <section>
        <h2>Details</h2>
        <p>Issue date: {formatDate(invoice.issue_date)}</p>
        <p>Due date: {formatDate(invoice.due_date)}</p>
        {invoice.cancelled_at && <p>Cancelled: {formatDate(invoice.cancelled_at)} — {invoice.cancellation_reason}</p>}
      </section>

      <section>
        <h2>Line Items</h2>
        <Table>
          <thead>
            <tr>
              <th>Description</th>
              <th>Qty</th>
              <th>Unit Price</th>
              <th>Tax</th>
              <th>Line Total</th>
            </tr>
          </thead>
          <tbody>
            {invoice.line_items.map((li) => (
              <tr key={li.id}>
                <td>{li.description}</td>
                <td>{li.quantity}</td>
                <td>{formatMoney(li.unit_price)}</td>
                <td>{li.tax_rate_snapshot ?? '—'}</td>
                <td>{formatMoney(li.line_total)}</td>
              </tr>
            ))}
          </tbody>
        </Table>
        <div style={{ marginTop: '0.5rem' }}>
          <p>Subtotal: {formatMoney(invoice.subtotal)}</p>
          <p>Tax: {formatMoney(invoice.tax_amount)}</p>
          <p data-testid="invoice-total">
            <strong>Total: {formatMoney(invoice.total_amount)}</strong>
          </p>
          <p>Paid: {formatMoney(invoice.amount_paid)}</p>
        </div>
      </section>

      <section>
        <h2>Payments</h2>
        {paymentsLoading ? <Spinner /> : <PaymentHistoryTable payments={payments ?? []} />}
        {canRecordPayment && <PaymentForm invoiceId={invoice.id} maxAllowed={maxAllowedPayment} />}
      </section>

      <section>
        <h2>Reminders</h2>
        {remindersLoading ? <Spinner /> : <ReminderHistoryTable invoiceId={invoice.id} reminders={reminders ?? []} />}
      </section>

      {showCancelDialog && (
        <CancelInvoiceDialog
          isPending={cancelInvoice.isPending}
          error={cancelError}
          onClose={() => setShowCancelDialog(false)}
          onConfirm={(reason) => {
            setCancelError(null);
            cancelInvoice.mutate(
              { reason },
              {
                onSuccess: () => {
                  setShowCancelDialog(false);
                  showToast('Invoice cancelled');
                },
                onError: (err) => setCancelError(err),
              },
            );
          }}
        />
      )}
    </div>
  );
}
