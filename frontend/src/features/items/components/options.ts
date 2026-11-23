import { useI18n } from 'vue-i18n'
import type { Schemas } from '@/api/types'
import { allValues } from '@/utils/enums'

/** The values of the copy's choice fields, checked against the backend's enums. */
export const CHOICES = {
  format: allValues<Schemas['ItemFormat']>({ physical: true, digital: true }),
  status: allValues<Schemas['ItemStatus']>({ owned: true, sold: true }),
  condition: allValues<Schemas['Condition']>({
    new: true,
    like_new: true,
    good: true,
    acceptable: true,
    poor: true,
  }),
  completeness: allValues<Schemas['Completeness']>({
    sealed: true,
    complete: true,
    box_and_game: true,
    loose: true,
  }),
  play_status: allValues<Schemas['PlayStatus']>({
    unplayed: true,
    playing: true,
    finished: true,
    completed: true,
    abandoned: true,
  }),
  region: allValues<Schemas['Region']>({
    pal: true,
    de: true,
    uk: true,
    fr: true,
    na: true,
    jp: true,
    asia: true,
    kr: true,
    world: true,
    other: true,
  }),
}

/** Translated {value, label} options for a choice field. */
export function useChoiceOptions() {
  const { t } = useI18n()
  return (field: keyof typeof CHOICES) =>
    CHOICES[field].map((value) => ({ value, label: t(`choices.${field}.${value}`) }))
}
