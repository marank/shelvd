/**
 * Release dates with precision ("28.04.2017", "März 2026", "Q3 2026", "TBA") and a
 * relative hint ("in 3 Wochen"), like the catalog stores them: the first day of the
 * period plus a precision (backend: apps/catalog/models/dates.py).
 */
import type { Release, Schemas } from '@/api/types'
import { allValues } from '@/utils/enums'

export type Precision = Schemas['DatePrecision']
export const PRECISIONS = allValues<Precision>({
  day: true,
  week: true,
  month: true,
  quarter: true,
  half: true,
  year: true,
  window: true,
  tba: true,
})

type Dated = Pick<Release, 'release_date' | 'release_date_end' | 'release_precision'>

function parse(value: string | null | undefined): Date | null {
  if (!value) return null
  const [y, m, d] = value.split('-').map(Number)
  return new Date(y!, (m ?? 1) - 1, d ?? 1)
}

function isoWeek(date: Date): number {
  const target = new Date(
    date.getFullYear(),
    date.getMonth(),
    date.getDate() + 3 - ((date.getDay() + 6) % 7),
  )
  const firstThursday = new Date(target.getFullYear(), 0, 4)
  return 1 + Math.round((target.getTime() - firstThursday.getTime()) / 604_800_000)
}

/** Label for the date, or "" when there is none (and the precision isn't TBA). */
export function formatReleaseDate(release: Dated, locale: string, tba = 'TBA'): string {
  const precision = release.release_precision
  if (precision === 'tba') return tba
  const start = parse(release.release_date)
  if (!start) return ''
  const year = start.getFullYear()
  const fmt = (options: Intl.DateTimeFormatOptions, date = start) =>
    new Intl.DateTimeFormat(locale, options).format(date)
  switch (precision) {
    case 'week':
      return `${locale.startsWith('de') ? 'KW' : 'Week'} ${isoWeek(start)} ${year}`
    case 'month':
      return fmt({ month: 'long', year: 'numeric' })
    case 'quarter':
      return `Q${Math.floor(start.getMonth() / 3) + 1} ${year}`
    case 'half':
      return `H${start.getMonth() < 6 ? 1 : 2} ${year}`
    case 'year':
      return String(year)
    case 'window': {
      const end = parse(release.release_date_end) ?? start
      const short: Intl.DateTimeFormatOptions = { day: '2-digit', month: '2-digit' }
      return `${fmt(short)}–${fmt({ ...short, year: 'numeric' }, end)}`
    }
    case 'day':
      return fmt({ day: '2-digit', month: '2-digit', year: 'numeric' })
  }
}

/** Last day of the period; null when unknown. */
export function periodEnd(release: Dated): Date | null {
  const precision = release.release_precision
  const start = parse(release.release_date)
  if (precision === 'tba' || !start) return null
  const y = start.getFullYear()
  const m = start.getMonth()
  switch (precision) {
    case 'week':
      return new Date(y, m, start.getDate() + 6)
    case 'month':
      return new Date(y, m + 1, 0)
    case 'quarter':
      return new Date(y, Math.floor(m / 3) * 3 + 3, 0)
    case 'half':
      return new Date(y, m < 6 ? 6 : 12, 0)
    case 'year':
      return new Date(y, 12, 0)
    case 'window':
      return parse(release.release_date_end) ?? start
    case 'day':
      return start
  }
}

/**
 * "today", "in 5 days", "in 3 weeks", "next month" … for future dates; "" for past or
 * unknown ones. Coarse precisions only get month/year granularity.
 */
export function relativeHint(release: Dated, locale: string, now = new Date()): string {
  const precision = release.release_precision
  const start = parse(release.release_date)
  const end = periodEnd(release)
  if (!start || !end) return ''
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  if (end < today) return ''
  const rtf = new Intl.RelativeTimeFormat(locale, { numeric: 'auto' })
  const fine = precision === 'day' || precision === 'week' || precision === 'window'
  const target = fine ? start : end
  const days = Math.round((target.getTime() - today.getTime()) / 86_400_000)
  if (fine && days <= 0) return rtf.format(0, 'day')
  if (fine && days < 7) return rtf.format(days, 'day')
  if (fine && days < 35) return rtf.format(Math.round(days / 7), 'week')
  const months =
    (target.getFullYear() - today.getFullYear()) * 12 + target.getMonth() - today.getMonth()
  if (months < 12) return rtf.format(Math.max(months, 0), 'month')
  return rtf.format(target.getFullYear() - today.getFullYear(), 'year')
}

/** Out yet? Mirrors the backend's is_released, for client-side grouping. */
export function isOut(release: Dated, now = new Date()): boolean {
  const end = periodEnd(release)
  return !!end && end <= now
}
