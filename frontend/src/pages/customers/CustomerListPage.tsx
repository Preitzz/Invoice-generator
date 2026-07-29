import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useCustomers, useCreateCustomer } from '../../hooks/useCustomers';
import { useRole } from '../../hooks/useRole';
import { Spinner } from '../../components/ui/Spinner';
import { ErrorBanner } from '../../components/common/ErrorBanner';
import { EmptyState } from '../../components/ui/EmptyState';
import { Table } from '../../components/ui/Table';
import { Button } from '../../components/ui/Button';
import { Modal } from '../../components/ui/Modal';
import { CustomerForm } from '../../components/customers/CustomerForm';
import { useToast } from '../../components/ui/Toast';

export function CustomerListPage() {
  const { data, isLoading, error, refetch } = useCustomers();
  const { isStaff } = useRole();
  const createCustomer = useCreateCustomer();
  const { showToast } = useToast();
  const [showCreate, setShowCreate] = useState(false);
  const [createError, setCreateError] = useState<unknown>(null);

  if (isLoading) return <Spinner />;
  if (error) return <ErrorBanner error={error} onRetry={() => refetch()} />;

  return (
    <div data-testid="customer-list-page">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h1>Customers</h1>
        {isStaff && (
          <Button variant="primary" onClick={() => setShowCreate(true)} data-testid="btn-new-customer">
            New Customer
          </Button>
        )}
      </div>

      {data && data.length === 0 ? (
        <EmptyState message="No customers yet." />
      ) : (
        <Table>
          <thead>
            <tr>
              <th>Name</th>
              <th>Email</th>
              <th>Phone</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {data?.map((c) => (
              <tr key={c.id} data-testid={`customer-row-${c.id}`}>
                <td>
                  <Link to={`/customers/${c.id}`}>{c.name}</Link>
                </td>
                <td>{c.email}</td>
                <td>{c.phone ?? '—'}</td>
                <td>{c.is_active ? 'Active' : 'Inactive'}</td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}

      {showCreate && (
        <Modal title="New Customer" onClose={() => setShowCreate(false)} testId="customer-create-modal">
          {createError ? <ErrorBanner error={createError} /> : null}
          <CustomerForm
            isSubmitting={createCustomer.isPending}
            onSubmit={(values) => {
              setCreateError(null);
              createCustomer.mutate(values, {
                onSuccess: () => {
                  setShowCreate(false);
                  showToast('Customer created');
                },
                onError: (err) => setCreateError(err),
              });
            }}
          />
        </Modal>
      )}
    </div>
  );
}
