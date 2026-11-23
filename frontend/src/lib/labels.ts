import { useI18n } from 'vue-i18n'
import { firstText } from './utils'
import { NONE_KEY } from '@/api/types'
import { fieldChoice, useChoiceLabel } from './itemFields'

/** Fields grouped by month ("2026-03"). */
const MONTH_FIELDS: string[] = ['copy.added', 'copy.acquired']

/** Human label for a group node or a filter value: choices are translated. */
export function useGroupLabel() {
  const { t, locale } = useI18n()
  const choiceLabel = useChoiceLabel()
  // Any field key: group fields get their special labels, the rest reads plainly.
  return (field: string, key: string, label = ''): string => {
    if (key === NONE_KEY) return t('groups.none')
    const month = MONTH_FIELDS.includes(field) ? /^(\d{4})-(\d{2})$/.exec(key) : null
    if (month) {
      const day = new Date(Number(month[1]), Number(month[2]) - 1, 1)
      return day.toLocaleDateString(locale.value, { month: 'long', year: 'numeric' })
    }
    const choice = fieldChoice(field)
    return choice ? choiceLabel(choice, key) : label || key
  }
}

/** A platform's own colour, else its manufacturer's. */
export function platformColor(platform: { manufacturer: string; color?: string }): string {
  return firstText(platform.color) ?? brandColor(platform.manufacturer)
}

/** Manufacturer → CSS color token for the small platform dot. */
export function brandColor(manufacturer: string): string {
  const key = manufacturer.toLowerCase()
  if (['nintendo', 'sony', 'microsoft', 'sega'].includes(key)) return `var(--brand-${key})`
  return 'var(--brand-other)'
}
