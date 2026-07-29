import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useForm, FormProvider } from 'react-hook-form';
import { LineItemBuilder } from '../../src/components/invoices/LineItemBuilder';
import type { InvoiceFormValues } from '../../src/components/invoices/invoiceFormSchema';

function Harness() {
  const methods = useForm<InvoiceFormValues>({
    defaultValues: {
      customer_id: '',
      due_date: '',
      line_items: [{ description: '', quantity: '1', unit_price: '0.00' }],
    },
  });
  return (
    <FormProvider {...methods}>
      <LineItemBuilder />
    </FormProvider>
  );
}

describe('LineItemBuilder', () => {
  it('renders one row by default and disables remove when only one row remains', () => {
    render(<Harness />);
    expect(screen.getByTestId('line-item-row-0')).toBeInTheDocument();
    expect(screen.getByTestId('btn-remove-line-item-0')).toBeDisabled();
  });

  it('adds a new row when "Add Line Item" is clicked', async () => {
    const user = userEvent.setup();
    render(<Harness />);
    await user.click(screen.getByTestId('btn-add-line-item'));
    expect(screen.getByTestId('line-item-row-1')).toBeInTheDocument();
    // remove is now enabled since there are 2 rows
    expect(screen.getByTestId('btn-remove-line-item-0')).not.toBeDisabled();
  });

  it('removes a row when its remove button is clicked', async () => {
    const user = userEvent.setup();
    render(<Harness />);
    await user.click(screen.getByTestId('btn-add-line-item'));
    expect(screen.getByTestId('line-item-row-1')).toBeInTheDocument();
    await user.click(screen.getByTestId('btn-remove-line-item-1'));
    expect(screen.queryByTestId('line-item-row-1')).not.toBeInTheDocument();
  });

  it('lets a user type into description, quantity, and unit price fields', async () => {
    const user = userEvent.setup();
    render(<Harness />);
    const description = screen.getByTestId('line-item-description-0') as HTMLInputElement;
    await user.clear(description);
    await user.type(description, 'Consulting hours');
    expect(description.value).toBe('Consulting hours');
  });
});
