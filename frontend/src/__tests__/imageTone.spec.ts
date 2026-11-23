import { describe, expect, it } from 'vitest'
import { RIMS, rimFor } from '@/lib/imageTone'

describe('image tone', () => {
  it('inverts one-colour logos and outlines the rest', () => {
    expect(rimFor('black')).toBe(RIMS.black)
    expect(rimFor('light')).toBe(RIMS.light)
    expect(rimFor('')).toBe('')
    expect(rimFor(null)).toBe('')
    expect(rimFor('purple')).toBe('') // unknown: as it is
  })

  it('never inverts a photo', () => {
    expect(rimFor('black', true)).toBe(RIMS.dark)
    expect(rimFor('white', true)).toBe(RIMS.light)
    expect(rimFor('dark', true)).toBe(RIMS.dark)
  })
})
