export function isCurrentOrPreviousMonth(value: string, now = new Date()): boolean {
  if (!value) {
    return false;
  }
  const date = new Date(`${value}T00:00:00`);
  if (Number.isNaN(date.getTime())) {
    return false;
  }
  const current = monthKey(now);
  const previous = monthKey(new Date(now.getFullYear(), now.getMonth() - 1, 1));
  return monthKey(date) === current || monthKey(date) === previous;
}

export function defaultMealDate(now = new Date()): string {
  return now.toISOString().slice(0, 10);
}

function monthKey(value: Date): string {
  return `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, '0')}`;
}
