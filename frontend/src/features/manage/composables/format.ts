/** Today as YYYY-MM-DD in local time (what a date input expects). */
export function todayIso(now = new Date()): string {
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`
}

/** Format an ISO date (YYYY-MM-DD) for display without shifting it across time zones. */
export function formatDate(value: string | null | undefined, locale: string): string {
  if (!value) return ''
  const date = new Date(`${value.slice(0, 10)}T00:00:00Z`)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleDateString(locale, { timeZone: 'UTC', dateStyle: 'medium' })
}

/** The backend's message for a failed request. */
export function errorMessage(error: unknown, fallback: string): string {
  return error instanceof Error && error.message ? error.message : fallback
}
