import { useFieldArray, useFormContext, type FieldValues } from 'react-hook-form';
import { Button } from '../ui/Button';
import { Input } from '../ui/Input';
import { DecimalInput } from '../common/DecimalInput';
import { Table } from '../ui/Table';
import type { LineItemCreate } from '../../types/invoice';

interface WithLineItems extends FieldValues {
  line_items: LineItemCreate[];
}

/**
 * Dynamic line-item row editor for invoice create/edit forms. Works for any
 * react-hook-form values shape that includes `line_items` — the create form
 * (which also has customer_id) and the edit form (which doesn't) both provide
 * a FormProvider whose value shape is compatible with WithLineItems.
 */
export function LineItemBuilder() {
  const { control, register, formState } = useFormContext<WithLineItems>();
  const { fields, append, remove } = useFieldArray({ control, name: 'line_items' });
  const errors = formState.errors.line_items;

  return (
    <div data-testid="line-item-builder">
      <Table>
        <thead>
          <tr>
            <th>Description</th>
            <th>Quantity</th>
            <th>Unit Price</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {fields.map((field, index) => (
            <tr key={field.id} data-testid={`line-item-row-${index}`}>
              <td>
                <Input
                  {...register(`line_items.${index}.description` )}
                  data-testid={`line-item-description-${index}`}
                />
                {errors?.[index]?.description && (
                  <span data-testid={`line-item-error-${index}`}>{errors[index]?.description?.message}</span>
                )}
              </td>
              <td>
                <DecimalInput
                  {...register(`line_items.${index}.quantity` )}
                  step="1"
                  data-testid={`line-item-quantity-${index}`}
                />
              </td>
              <td>
                <DecimalInput
                  {...register(`line_items.${index}.unit_price` )}
                  data-testid={`line-item-unit-price-${index}`}
                />
              </td>
              <td>
                <Button
                  type="button"
                  variant="danger"
                  onClick={() => remove(index)}
                  disabled={fields.length <= 1}
                  data-testid={`btn-remove-line-item-${index}`}
                >
                  Remove
                </Button>
              </td>
            </tr>
          ))}
        </tbody>
      </Table>
      <Button
        type="button"
        onClick={() => append({ description: '', quantity: '1', unit_price: '0.00' })}
        data-testid="btn-add-line-item"
      >
        Add Line Item
      </Button>
    </div>
  );
}
