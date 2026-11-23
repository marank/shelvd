/**
 * Group tracking entries like a release calendar: out already first, then month by
 * month, coarse dates (quarter, half, year) at the end of their year, TBA last.
 */
import type { Tracking } from '@/api/types'

type GroupKind = 'released' | 'month' | 'year' | 'tba'

export interface TrackingGroup {
  key: string
  kind: GroupKind
  /** Month groups: "November 2026"; year groups: "2027"; '' for released/tba. */
  label: string
  entries: Tracking[]
}

const FINE = new Set(['day', 'week', 'month', 'window'])

function placeOf(entry: Tracking): { key: string; kind: GroupKind } {
  const release = entry.release
  if (release.is_released) return { key: '0', kind: 'released' }
  const date = release.release_date
  if (release.release_precision === 'tba' || !date) return { key: '9', kind: 'tba' }
  if (FINE.has(release.release_precision)) {
    return { key: `1-${release.sort_date.slice(0, 7)}`, kind: 'month' }
  }
  // Coarse: sorts after December of its year ("-13").
  return { key: `1-${date.slice(0, 4)}-13`, kind: 'year' }
}

function label(kind: GroupKind, key: string, locale: string): string {
  if (kind === 'month') {
    const [y, m] = key.slice(2).split('-').map(Number)
    return new Intl.DateTimeFormat(locale, { month: 'long', year: 'numeric' }).format(
      new Date(y!, m! - 1, 1),
    )
  }
  if (kind === 'year') return key.slice(2, 6)
  return ''
}

function byDate(a: Tracking, b: Tracking): number {
  return (
    a.release.sort_date.localeCompare(b.release.sort_date) ||
    a.release.title.localeCompare(b.release.title)
  )
}

export function groupTrackings(entries: Tracking[], locale: string): TrackingGroup[] {
  const groups = new Map<string, TrackingGroup>()
  for (const entry of entries) {
    const { key, kind } = placeOf(entry)
    let group = groups.get(key)
    if (!group) {
      group = { key, kind, label: label(kind, key, locale), entries: [] }
      groups.set(key, group)
    }
    group.entries.push(entry)
  }
  return [...groups.values()]
    .sort((a, b) => a.key.localeCompare(b.key))
    .map((g) => ({ ...g, entries: [...g.entries].sort(byDate) }))
}
