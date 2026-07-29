// Amounts arrive from the backend as decimal strings. Never parse to float
// for arithmetic — only for display formatting.
export function formatMoney(amount: string | number, currency = 'INR'): string {
  const num = typeof amount === 'string' ? Number(amount) : amount;
  if (Number.isNaN(num)) return amount.toString();
  try {
    return new Intl.NumberFormat('en-IN', { style: 'currency', currency, minimumFractionDigits: 2 }).format(num);
  } catch {
    return num.toFixed(2);
  }
}
