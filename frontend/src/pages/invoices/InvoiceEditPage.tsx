import { useEffect, useState } from 'react';
import { FormProvider, useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useNavigate, useParams } from 'react-router-dom';
import { useInvoice, useUpdateInvoice } from '../../hooks/useInvoices';
import { LineItemBuilder } from '../../components/invoices/LineItemBuilder';
import { invoiceEditFormSchema, type InvoiceEditFormValues } from '../../components/invoices/invoiceFormSchema';
import { Button } from '../../components/ui/Button';
import { FormField } from '../../components/ui/FormField';
import { Input } from '../../components/ui/Input';
import { ErrorBanner } from '../../components/common/ErrorBanner';
import { Spinner } from '../../components/ui/Spinner';
import { useToast } from '../../components/ui/Toast';

export function InvoiceEditPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { data: invoice, isLoading, error } = useInvoice(id);
  const updateInvoice = useUpdateInvoice(id ?? '');
  const { showToast } = useToast();
  const [submitError, setSubmitError] = useState<unknown>(null);

  const methods = useForm<InvoiceEditFormValues>({
    resolver: zodResolver(invoiceEditFormSchema),
    defaultValues: { due_date: '', line_items: [{ description: '', quantity: '1', unit_price: '0.00' }] },
  });

  useEffect(() => {
    if (invoice) {
      methods.reset({
        due_date: invoice.due_date,
        line_items: invoice.line_items.map((li) => ({
          description: li.description,
          quantity: li.quantity,
          unit_price: li.unit_price,
        })),
      });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [invoice]);

  if (isLoading) return <Spinner />;
  if (error) return <ErrorBanner error={error} />;
  if (!invoice) return null;

  const isEditable = !['paid', 'cancelled'].includes(invoice.status);
  if (!isEditable) {
    return (
      <div data-testid="invoice-edit-blocked">
        <ErrorBanner error={new Error('This invoice can no longer be edited.')} />
        <Button type="button" onClick={() => navigate(`/invoices/${invoice.id}`)}>
          Back to invoice
        </Button>
      </div>
    );
  }

  const onSubmit = (values: InvoiceEditFormValues) => {
    setSubmitError(null);
    updateInvoice.mutate(values, {
      onSuccess: () => {
        showToast('Invoice updated');
        navigate(`/invoices/${invoice.id}`);
      },
      onError: (err) => setSubmitError(err),
    });
  };

  return (
    <div data-testid="invoice-edit-page">
      <h1>Edit Invoice</h1>
      {submitError ? <ErrorBanner error={submitError} /> : null}
      <FormProvider {...methods}>
        <form onSubmit={methods.handleSubmit(onSubmit)} data-testid="invoice-edit-form">
          <FormField name="due_date" label="Due Date" error={methods.formState.errors.due_date?.message}>
            <Input type="date" {...methods.register('due_date')} data-testid="invoice-form-due-date" />
          </FormField>
          <LineItemBuilder />
          <div style={{ display: 'flex', gap: '0.5rem', marginTop: '1rem' }}>
            <Button type="submit" variant="primary" disabled={updateInvoice.isPending} data-testid="btn-save-invoice-edit">
              {updateInvoice.isPending ? 'Saving…' : 'Save Changes'}
            </Button>
            <Button type="button" onClick={() => navigate(`/invoices/${invoice.id}`)}>
              Cancel
            </Button>
          </div>
        </form>
      </FormProvider>
    </div>
  );
}
