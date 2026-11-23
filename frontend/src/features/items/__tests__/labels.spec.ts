import { describe, expect, it } from 'vitest'
import { makeItem, makeRelease } from '@/test/fixtures'
import { copyLabel } from '../composables/labels'

describe('copyLabel', () => {
  it('names platform, region and edition, short names first', () => {
    const release = makeRelease({ edition: 'Steelbook' })
    expect(copyLabel(makeItem({ release }))).toBe(
      `${release.platform.short_name || release.platform.name} · ${release.region.toUpperCase()} · Steelbook`,
    )
    const unnamed = makeRelease({ platform: { ...release.platform, short_name: '' }, edition: '' })
    expect(copyLabel(makeItem({ release: unnamed }))).toBe(
      `${release.platform.name} · ${release.region.toUpperCase()}`,
    )
  })
})
