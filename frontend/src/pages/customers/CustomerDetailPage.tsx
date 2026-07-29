import { useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { useCustomer, useDeactivateCustomer, useUpdateCustomer } from '../../hooks/useCustomers';
import { useRole } from '../../hooks/useRole';
import { Spinner } from '../../components/ui/Spinner';
import { ErrorBanner } from '../../components/common/ErrorBanner';
import { Button } from '../../components/ui/Button';
import { ConfirmDialog } from '../../components/ui/ConfirmDialog';
import { CustomerForm } from '../../components/customers/CustomerForm';
import { useToast } from '../../components/ui/Toast';

export function CustomerDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { data, isLoading, error, refetch } = useCustomer(id);
  const { isStaff } = useRole();
  const updateCustomer = useUpdateCustomer(id ?? '');
  const deactivateCustomer = useDeactivateCustomer(id ?? '');
  const { showToast } = useToast();
  const [isEditing, setIsEditing] = useState(false);
  const [showDeactivateConfirm, setShowDeactivateConfirm] = useState(false);
  const [formError, setFormError] = useState<unknown>(null);
  const [deactivateError, setDeactivateError] = useState<unknown>(null);

  if (isLoading) return <Spinner />;
  if (error) return <ErrorBanner error={error} onRetry={() => refetch()} />;
  if (!data) return null;

  return (
    <div data-testid="customer-detail-page">
      <h1 data-testid="customer-name">{data.name}</h1>
      <p>Status: {data.is_active ? 'Active' : 'Inactive'}</p>

      {deactivateError ? <ErrorBanner error={deactivateError} /> : null}

      {isEditing ? (
        <>
          {formError ? <ErrorBanner error={formError} /> : null}
          <CustomerForm
            initial={data}
            isSubmitting={updateCustomer.isPending}
            submitLabel="Save Changes"
            onSubmit={(values) => {
              setFormError(null);
              updateCustomer.mutate(values, {
                onSuccess: () => {
                  setIsEditing(false);
                  showToast('Customer updated');
                },
                onError: (err) => setFormError(err),
              });
            }}
          />
          <Button type="button" onClick={() => setIsEditing(false)}>
            Cancel
          </Button>
        </>
      ) : (
        <div data-testid="customer-details">
          <p>Email: {data.email}</p>
          <p>Phone: {data.phone ?? '—'}</p>
          <p>Billing Address: {data.billing_address}</p>
          {isStaff && (
            <div style={{ display: 'flex', gap: '0.5rem', marginTop: '1rem' }}>
              <Button type="button" onClick={() => setIsEditing(true)} data-testid="btn-edit-customer">
                Edit
              </Button>
              {data.is_active && (
                <Button
                  type="button"
                  variant="danger"
                  onClick={() => setShowDeactivateConfirm(true)}
                  data-testid="btn-deactivate-customer"
                >
                  Deactivate
                </Button>
              )}
            </div>
          )}
          <div style={{ marginTop: '1rem', display: 'flex', gap: '1rem' }}>
            <Link to={`/reports/customer/${data.id}`}>View statement</Link>
            <Link to={`/invoices?customer_id=${data.id}`}>View invoices</Link>
          </div>
        </div>
      )}

      {showDeactivateConfirm && (
        <ConfirmDialog
          title="Deactivate customer"
          message={`Are you sure you want to deactivate ${data.name}? This cannot be undone if the customer has no open invoices.`}
          confirmLabel="Deactivate"
          confirmTestId="confirm-deactivate-customer"
          isPending={deactivateCustomer.isPending}
          onCancel={() => setShowDeactivateConfirm(false)}
          onConfirm={() => {
            setDeactivateError(null);
            deactivateCustomer.mutate(undefined, {
              onSuccess: () => {
                setShowDeactivateConfirm(false);
                showToast('Customer deactivated');
              },
              onError: (err) => {
                setDeactivateError(err);
                setShowDeactivateConfirm(false);
              },
            });
          }}
        />
      )}

      <div style={{ marginTop: '1.5rem' }}>
        <Button type="button" onClick={() => navigate('/customers')}>
          Back to Customers
        </Button>
      </div>
    </div>
  );
}
