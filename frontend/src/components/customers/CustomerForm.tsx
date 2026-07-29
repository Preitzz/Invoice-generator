import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Button } from '../ui/Button';
import { FormField } from '../ui/FormField';
import { Input } from '../ui/Input';
import { TextArea } from '../ui/TextArea';
import type { CustomerCreate, CustomerRead } from '../../types/customer';

const schema = z.object({
  name: z.string().min(1, 'Name is required'),
  email: z.string().email('Enter a valid email'),
  phone: z.string().optional(),
  billing_address: z.string().min(1, 'Billing address is required'),
});

type FormValues = z.infer<typeof schema>;

interface CustomerFormProps {
  initial?: CustomerRead;
  onSubmit: (values: CustomerCreate) => void;
  isSubmitting?: boolean;
  submitLabel?: string;
}

export function CustomerForm({ initial, onSubmit, isSubmitting, submitLabel = 'Save' }: CustomerFormProps) {
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      name: initial?.name ?? '',
      email: initial?.email ?? '',
      phone: initial?.phone ?? '',
      billing_address: initial?.billing_address ?? '',
    },
  });

  return (
    <form
      data-testid="customer-form"
      onSubmit={handleSubmit((values) =>
        onSubmit({ ...values, phone: values.phone || undefined }),
      )}
    >
      <FormField name="name" label="Name" error={errors.name?.message}>
        <Input {...register('name')} data-testid="customer-form-name" />
      </FormField>
      <FormField name="email" label="Email" error={errors.email?.message}>
        <Input {...register('email')} type="email" data-testid="customer-form-email" />
      </FormField>
      <FormField name="phone" label="Phone">
        <Input {...register('phone')} data-testid="customer-form-phone" />
      </FormField>
      <FormField name="billing_address" label="Billing Address" error={errors.billing_address?.message}>
        <TextArea {...register('billing_address')} data-testid="customer-form-address" />
      </FormField>
      <Button type="submit" variant="primary" disabled={isSubmitting} data-testid="customer-form-submit">
        {isSubmitting ? 'Saving…' : submitLabel}
      </Button>
    </form>
  );
}
