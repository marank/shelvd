export const LOCALES = ['de', 'en'] as const
export type Locale = (typeof LOCALES)[number]

export type Messages = Record<string, unknown>

// Keys that would reach Object.prototype instead of the message tree.
const UNSAFE = new Set(['__proto__', 'constructor', 'prototype'])

function merge(target: Messages, source: Messages): Messages {
  for (const [key, value] of Object.entries(source)) {
    if (UNSAFE.has(key)) continue
    const existing = target[key]
    if (value && typeof value === 'object' && existing && typeof existing === 'object') {
      merge(existing as Messages, value as Messages)
    } else {
      target[key] = value
    }
  }
  return target
}

/** Merges message files by language, read from the file name (`…/de.json`). */
export function collectMessages(sources: Record<string, Messages>): Record<Locale, Messages> {
  const messages: Record<Locale, Messages> = { de: {}, en: {} }
  for (const [path, content] of Object.entries(sources)) {
    const lang = path.split('/').pop()?.replace('.json', '') as Locale
    if (LOCALES.includes(lang)) merge(messages[lang], content)
  }
  return messages
}
