import { describe, expect, it } from 'vitest'
import { ApiError } from '@/api/errors'
import { errorMessage, formatDate, todayIso } from '../composables/format'

describe('format helpers', () => {
  it('formats dates without shifting time zones', () => {
    expect(formatDate('2026-03-01', 'en')).toBe('Mar 1, 2026')
    expect(formatDate('2026-03-01', 'de')).toBe('01.03.2026')
    expect(formatDate(null, 'en')).toBe('')
    expect(formatDate('garbage', 'en')).toBe('garbage')
  })

  it('builds a local ISO date', () => {
    expect(todayIso(new Date(2026, 0, 5, 23, 59))).toBe('2026-01-05')
  })

  it('picks the backend message or a fallback', () => {
    expect(errorMessage(new ApiError(409, 'Busy.'), 'x')).toBe('Busy.')
    expect(errorMessage(new Error(''), 'Fallback')).toBe('Fallback')
    expect(errorMessage('nope', 'Fallback')).toBe('Fallback')
  })
})
