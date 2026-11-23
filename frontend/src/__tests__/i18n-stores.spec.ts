import { createPinia, setActivePinia } from 'pinia'
import { describe, expect, it, vi } from 'vitest'
import { nextTick } from 'vue'
import { collectMessages, detectLocale, i18n, setLocale } from '@/i18n'
import { brandColor } from '@/lib/labels'
import { useAuthStore } from '@/stores/auth'
import { useUiStore } from '@/stores/ui'
import { mockApi, testUser } from '@/test/utils'

describe('i18n', () => {
  it('merges feature messages per language', () => {
    const messages = collectMessages({
      './locales/de.json': { a: { b: 'x' } },
      '../features/f/locales/de.json': { a: { c: 'y' }, d: 'z' },
      '../features/f/locales/fr.json': { ignored: true },
    })
    expect(messages.de).toEqual({ a: { b: 'x', c: 'y' }, d: 'z' })
    expect(messages.en).toEqual({})
  })

  it('detects the language from storage, then the browser', () => {
    expect(detectLocale('en', ['de-DE'])).toBe('en')
    expect(detectLocale(null, ['fr-FR', 'en-US'])).toBe('en')
    expect(detectLocale('xx', ['fr'])).toBe('de')
    expect(detectLocale(null, [])).toBe('de')
  })

  it('has the same keys in every language', async () => {
    const keys = (messages: object, prefix = ''): string[] =>
      Object.entries(messages).flatMap(([key, value]) =>
        value && typeof value === 'object' ? keys(value, `${prefix}${key}.`) : [prefix + key],
      )
    const [de, en] = await Promise.all([import('@/i18n/messages/de'), import('@/i18n/messages/en')])
    expect(keys(de.default).sort()).toEqual(keys(en.default).sort())
  })

  it('switches and remembers the language', async () => {
    await setLocale('de')
    expect(i18n.global.locale.value).toBe('de')
    expect(document.documentElement.lang).toBe('de')
    expect(localStorage.getItem('shelvd.locale')).toBe('de')
    await setLocale('en')
  })
})

describe('stores', () => {
  it('applies and remembers the theme', async () => {
    setActivePinia(createPinia())
    const ui = useUiStore()
    expect(ui.theme).toBe('system')
    ui.setTheme('dark')
    await nextTick()
    expect(document.documentElement.classList.contains('dark')).toBe(true)
    expect(localStorage.getItem('shelvd.theme')).toBe('dark')
    ui.setTheme('light')
    await nextTick()
    expect(document.documentElement.classList.contains('dark')).toBe(false)
    ui.openAdd('lib', 'scan')
    expect([ui.addOpen, ui.addLibraryId, ui.addMode]).toEqual([true, 'lib', 'scan'])
    setActivePinia(createPinia())
    expect(useUiStore().theme).toBe('light')
  })

  it('survives blocked storage', () => {
    const spy = vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new Error('blocked')
    })
    setActivePinia(createPinia())
    expect(useUiStore().theme).toBe('system')
    expect(detectLocale(undefined, ['en'])).toBe('en')
    spy.mockRestore()
  })

  it('logs in and out', async () => {
    setActivePinia(createPinia())
    mockApi({
      'GET /api/auth/me': { status: 401, body: { detail: 'no' } },
      'POST /api/auth/logout': { status: 204 },
    })
    const auth = useAuthStore()
    expect(await auth.fetchMe()).toBeNull()
    auth.user = testUser
    await auth.logout()
    expect(auth.user).toBeNull()
    auth.user = testUser
    auth.clear()
    expect(auth.user).toBeNull()
  })

  it('maps manufacturers to brand colors', () => {
    expect(brandColor('Nintendo')).toBe('var(--brand-nintendo)')
    expect(brandColor('Atari')).toBe('var(--brand-other)')
  })
})
