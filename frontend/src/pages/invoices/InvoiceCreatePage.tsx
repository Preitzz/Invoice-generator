import { FormProvider, useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useNavigate } from 'react-router-dom';
import { useState } from 'react';
import { useCustomers } from '../../hooks/useCustomers';
import { useCreateInvoice } from '../../hooks/useInvoices';
import { LineItemBuilder } from '../../components/invoices/LineItemBuilder';
import { invoiceFormSchema, type InvoiceFormValues } from '../../components/invoices/invoiceFormSchema';
import { Button } from '../../components/ui/Button';
import { FormField } from '../../components/ui/FormField';
import { Input } from '../../components/ui/Input';
import { Select } from '../../components/ui/Select';
import { ErrorBanner } from '../../components/common/ErrorBanner';
import { Spinner } from '../../components/ui/Spinner';
import { useToast } from '../../components/ui/Toast';

export function InvoiceCreatePage() {
  const navigate = useNavigate();
  const { data: customers, isLoading: customersLoading } = useCustomers();
  const createInvoice = useCreateInvoice();
  const { showToast } = useToast();
  const [submitError, setSubmitError] = useState<unknown>(null);

  const methods = useForm<InvoiceFormValues>({
    resolver: zodResolver(invoiceFormSchema),
    defaultValues: {
      customer_id: '',
      due_date: '',
      line_items: [{ description: '', quantity: '1', unit_price: '0.00' }],
    },
  });

  if (customersLoading) return <Spinner />;

  const onSubmit = (values: InvoiceFormValues) => {
    setSubmitError(null);
    createInvoice.mutate(values, {
      onSuccess: (invoice) => {
        showToast('Invoice created');
        navigate(`/invoices/${invoice.id}`);
      },
      onError: (err) => setSubmitError(err),
    });
  };

  return (
    <div data-testid="invoice-create-page">
      <h1>New Invoice</h1>
      {submitError ? <ErrorBanner error={submitError} /> : null}
      <FormProvider {...methods}>
        <form onSubmit={methods.handleSubmit(onSubmit)} data-testid="invoice-create-form">
          <FormField name="customer_id" label="Customer" error={methods.formState.errors.customer_id?.message}>
            <Select {...methods.register('customer_id')} data-testid="invoice-form-customer">
              <option value="">Select a customer…</option>
              {customers?.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </Select>
          </FormField>
          <FormField name="due_date" label="Due Date" error={methods.formState.errors.due_date?.message}>
            <Input type="date" {...methods.register('due_date')} data-testid="invoice-form-due-date" />
          </FormField>
          <LineItemBuilder />
          <div style={{ marginTop: '1rem' }}>
            <Button type="submit" variant="primary" disabled={createInvoice.isPending} data-testid="btn-create-invoice">
              {createInvoice.isPending ? 'Creating…' : 'Create Invoice'}
            </Button>
          </div>
        </form>
      </FormProvider>
    </div>
  );
}
