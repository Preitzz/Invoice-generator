import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useCreateTaxRate, useTaxRates } from '../../hooks/useTaxRates';
import { useRole } from '../../hooks/useRole';
import { Spinner } from '../../components/ui/Spinner';
import { ErrorBanner } from '../../components/common/ErrorBanner';
import { Table } from '../../components/ui/Table';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { FormField } from '../../components/ui/FormField';
import { Input } from '../../components/ui/Input';
import { DecimalInput } from '../../components/common/DecimalInput';
import { useToast } from '../../components/ui/Toast';
import { formatDate } from '../../utils/date';

const schema = z.object({
  name: z.string().min(1, 'Name is required'),
  rate_percent: z.string().min(1, 'Rate is required').refine((v) => Number(v) >= 0, 'Rate must be non-negative'),
  effective_from: z.string().min(1, 'Effective date is required'),
});

type FormValues = z.infer<typeof schema>;

export function TaxRatePage() {
  const { data, isLoading, error, refetch } = useTaxRates();
  const { isAdmin } = useRole();
  const createTaxRate = useCreateTaxRate();
  const { showToast } = useToast();
  const [submitError, setSubmitError] = useState<unknown>(null);

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<FormValues>({ resolver: zodResolver(schema), defaultValues: { name: '', rate_percent: '', effective_from: '' } });

  if (isLoading) return <Spinner />;
  if (error) return <ErrorBanner error={error} onRetry={() => refetch()} />;

  const onSubmit = (values: FormValues) => {
    setSubmitError(null);
    createTaxRate.mutate(values, {
      onSuccess: () => {
        reset();
        showToast('Tax rate created');
      },
      onError: (err) => setSubmitError(err),
    });
  };

  return (
    <div data-testid="tax-rate-page">
      <h1>Tax Rates</h1>
      <Table>
        <thead>
          <tr>
            <th>Name</th>
            <th>Rate %</th>
            <th>Effective From</th>
            <th>Effective To</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {data?.map((rate) => (
            <tr key={rate.id} data-testid={`tax-rate-row-${rate.id}`}>
              <td>{rate.name}</td>
              <td>{rate.rate_percent}</td>
              <td>{formatDate(rate.effective_from)}</td>
              <td>{formatDate(rate.effective_to)}</td>
              <td>{rate.is_active ? <Badge tone="success">Active</Badge> : <Badge tone="muted">Superseded</Badge>}</td>
            </tr>
          ))}
        </tbody>
      </Table>

      {isAdmin && (
        <section style={{ marginTop: '2rem' }}>
          <h2>Create New Rate</h2>
          <p>Creating a new rate automatically supersedes the current active rate.</p>
          {submitError ? <ErrorBanner error={submitError} /> : null}
          <form onSubmit={handleSubmit(onSubmit)} data-testid="tax-rate-form">
            <FormField name="name" label="Name" error={errors.name?.message}>
              <Input {...register('name')} data-testid="tax-rate-form-name" />
            </FormField>
            <FormField name="rate_percent" label="Rate %" error={errors.rate_percent?.message}>
              <DecimalInput {...register('rate_percent')} data-testid="tax-rate-form-percent" />
            </FormField>
            <FormField name="effective_from" label="Effective From" error={errors.effective_from?.message}>
              <Input type="date" {...register('effective_from')} data-testid="tax-rate-form-effective-from" />
            </FormField>
            <Button type="submit" variant="primary" disabled={createTaxRate.isPending} data-testid="btn-create-tax-rate">
              {createTaxRate.isPending ? 'Creating…' : 'Create Tax Rate'}
            </Button>
          </form>
        </section>
      )}
    </div>
  );
}
