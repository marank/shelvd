import { describe, expect, it } from 'vitest'
import { countryName, languageName } from '@/lib/displayNames'

describe('display names', () => {
  it('names countries in the language, falling back to the code', () => {
    expect(countryName('jp', 'de')).toBe('Japan')
    expect(countryName('JP', 'en')).toBe('Japan')
    expect(countryName('', 'de')).toBe('')
    expect(countryName('1', 'de')).toBe('1')
  })

  it('names languages', () => {
    expect(languageName('en', 'de')).toBe('Englisch')
    expect(languageName('de', 'en')).toBe('German')
  })
})
