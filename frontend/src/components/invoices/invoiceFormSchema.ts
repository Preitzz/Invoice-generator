import { z } from 'zod';

export const lineItemSchema = z.object({
  description: z.string().min(1, 'Description is required'),
  quantity: z
    .string()
    .min(1, 'Quantity is required')
    .refine((v) => Number(v) > 0, 'Quantity must be greater than 0'),
  unit_price: z
    .string()
    .min(1, 'Unit price is required')
    .refine((v) => Number(v) >= 0, 'Unit price cannot be negative'),
});

export const invoiceFormSchema = z.object({
  customer_id: z.string().min(1, 'Customer is required'),
  due_date: z.string().min(1, 'Due date is required'),
  line_items: z.array(lineItemSchema).min(1, 'At least one line item is required'),
});

export type InvoiceFormValues = z.infer<typeof invoiceFormSchema>;

export const invoiceEditFormSchema = z.object({
  due_date: z.string().min(1, 'Due date is required'),
  line_items: z.array(lineItemSchema).min(1, 'At least one line item is required'),
});

export type InvoiceEditFormValues = z.infer<typeof invoiceEditFormSchema>;
