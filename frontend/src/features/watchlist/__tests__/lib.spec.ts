import { describe, expect, it } from 'vitest'
import { formatDay, formatPrice, today } from '../lib/format'
import { groupTrackings } from '../lib/groups'
import { tracking, upcoming } from './fixtures'

const entry = (id: string, overrides: Parameters<typeof upcoming>[0]) =>
  tracking({ id, release: upcoming({ title: id, ...overrides }) })

describe('groupTrackings', () => {
  it('orders months, coarse years and TBA; sorts by date then title', () => {
    const groups = groupTrackings(
      [
        entry('b-week', {
          release_precision: 'week',
          release_date: '2026-11-09',
          sort_date: '2026-11-09',
        }),
        entry('a-window', {
          release_precision: 'window',
          release_date: '2026-11-09',
          release_date_end: '2026-11-20',
          sort_date: '2026-11-09',
        }),
        entry('half', {
          release_precision: 'half',
          release_date: '2026-07-01',
          sort_date: '2026-12-31',
        }),
        entry('jan', {
          release_precision: 'day',
          release_date: '2027-01-05',
          sort_date: '2027-01-05',
        }),
        entry('no-date', { release_precision: 'day', release_date: null, sort_date: '9999-12-31' }),
        entry('year', {
          release_precision: 'year',
          release_date: '2027-01-01',
          sort_date: '2027-12-31',
        }),
      ],
      'en',
    )
    expect(groups.map((g) => [g.kind, g.label, g.entries.map((e) => e.id)])).toEqual([
      ['month', 'November 2026', ['a-window', 'b-week']],
      ['year', '2026', ['half']],
      ['month', 'January 2027', ['jan']],
      ['year', '2027', ['year']],
      ['tba', '', ['no-date']],
    ])
  })
})

describe('format helpers', () => {
  it('formats prices, days and today', () => {
    expect(formatPrice(null, 'de')).toBe('')
    expect(formatPrice('', 'de')).toBe('')
    expect(formatPrice('abc', 'de')).toBe('abc')
    expect(formatPrice('59.9', 'de')).toMatch(/59,90\s€/)
    expect(formatDay('2026-01-02', 'de')).toBe('02.01.2026')
    expect(today(new Date(2026, 0, 2))).toBe('2026-01-02')
  })
})
