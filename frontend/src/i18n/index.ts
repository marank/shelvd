import { createI18n } from 'vue-i18n'
import { setApiLanguage } from '@/api/client'

import { LOCALES, type Locale, type Messages } from './collect'

export { collectMessages, LOCALES, type Locale } from './collect'

const STORAGE_KEY = 'shelvd.locale'

/** One chunk per language (./messages), so a start only downloads the language in use. */
const loaders: Record<Locale, () => Promise<{ default: Messages }>> = {
  de: () => import('./messages/de'),
  en: () => import('./messages/en'),
}

function readStored(): string | null {
  try {
    return localStorage.getItem(STORAGE_KEY)
  } catch {
    return null
  }
}

export function detectLocale(stored = readStored(), browser = navigator.languages): Locale {
  if (stored && LOCALES.includes(stored as Locale)) return stored as Locale
  for (const lang of browser) {
    const short = lang.slice(0, 2).toLowerCase()
    if (LOCALES.includes(short as Locale)) return short as Locale
  }
  return 'de'
}

export const i18n = createI18n({
  legacy: false,
  locale: detectLocale(),
  // Filled by loadLocale. No fallback language: only the language in use is loaded, and
  // both languages have the same keys (checked by a test).
  messages: {} as Record<Locale, Record<string, string>>,
  datetimeFormats: {
    de: { short: { year: 'numeric', month: '2-digit', day: '2-digit' } },
    en: { short: { year: 'numeric', month: 'short', day: 'numeric' } },
  },
  numberFormats: {
    de: { currency: { style: 'currency', currency: 'EUR' } },
    en: { currency: { style: 'currency', currency: 'EUR' } },
  },
  missingWarn: false,
  fallbackWarn: false,
})

const loaded = new Set<Locale>()

/** Loads a language's messages once; call before showing it. */
export async function loadLocale(locale: Locale): Promise<void> {
  if (loaded.has(locale)) return
  const { default: messages } = await loaders[locale]()
  // Nested JSON objects; vue-i18n's message types can't express "any depth" from JSON.
  i18n.global.setLocaleMessage(locale, messages as Record<string, string>)
  loaded.add(locale)
}

export async function setLocale(locale: Locale): Promise<void> {
  await loadLocale(locale)
  i18n.global.locale.value = locale
  setApiLanguage(locale)
  document.documentElement.lang = locale
  try {
    localStorage.setItem(STORAGE_KEY, locale)
  } catch {
    // private mode: the choice just isn't remembered
  }
}
