import { describe, expect, it } from 'vitest'
import { justify } from '../composables/justify'

const options = { width: 500, rowHeight: 100, gap: 10, padding: 0 }

describe('justify', () => {
  it('fills full rows exactly and keeps the last row at the previous height', () => {
    // 0.7 + 0.7 + 1.1 + 1.1 → rows: [0,1,2,3] overflow at index 3 (natural 360+…)
    const widths = justify([1.1, 1.1, 1.1, 1.1, 1.1, 1.1], options)
    // Row 1: 4 covers × 1.1 at height h: 4.4h + 30 = 500 → h ≈ 106.8
    const height = (500 - 30) / 4.4
    expect(widths.slice(0, 4)).toEqual(Array(4).fill(Math.floor(1.1 * height)))
    // Last row (2 covers) has the same height, not the target 100 and not stretched.
    expect(widths.slice(4)).toEqual([Math.floor(1.1 * height), Math.floor(1.1 * height)])
  })

  it('keeps everything in one row when it fits and shrinks too-wide single covers', () => {
    expect(justify([0.6, 0.6], options)).toEqual([60, 60])
    // A panorama wider than the space: scaled down to fit.
    expect(justify([8], { ...options, padding: 12 })).toEqual([500])
    expect(justify([], options)).toEqual([])
  })
})
