/** Names of countries and languages in the UI language, from the browser (no lists of our
 * own); the code itself if the browser doesn't know it. */
function displayName(type: 'region' | 'language', code: string, locale: string): string {
  if (!code) return ''
  try {
    return new Intl.DisplayNames([locale], { type }).of(code) ?? code
  } catch {
    return code
  }
}

/** "JP" → "Japan" (ISO 3166-1 alpha-2). */
export const countryName = (code: string, locale: string) =>
  displayName('region', code.toUpperCase(), locale)

/** "en" → "Englisch". */
export const languageName = (code: string, locale: string) => displayName('language', code, locale)
