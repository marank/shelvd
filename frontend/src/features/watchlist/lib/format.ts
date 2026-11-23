/** "59,99 €" for a decimal string from the API; '' when there is none. */
export function formatPrice(value: string | number | null | undefined, locale: string): string {
  if (value === null || value === undefined || value === '') return ''
  const number = Number(value)
  if (Number.isNaN(number)) return String(value)
  return new Intl.NumberFormat(locale, { style: 'currency', currency: 'EUR' }).format(number)
}

/** "31.10.2026" for an ISO date. */
export function formatDay(value: string, locale: string): string {
  const [y, m, d] = value.split('-').map(Number)
  return new Intl.DateTimeFormat(locale, {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  }).format(new Date(y!, m! - 1, d))
}

/** Today as YYYY-MM-DD in local time. */
export function today(now = new Date()): string {
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`
}
