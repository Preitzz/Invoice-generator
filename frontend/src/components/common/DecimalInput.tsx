import type { InputHTMLAttributes } from 'react';
import { Input } from '../ui/Input';

// Numeric input constrained to 2dp for money-like fields. Kept as a plain
// string value all the way through so we never do float math client-side.
export function DecimalInput(props: InputHTMLAttributes<HTMLInputElement>) {
  return <Input type="number" step="0.01" inputMode="decimal" {...props} />;
}
