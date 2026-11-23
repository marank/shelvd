import type { ItemIn } from '@/api/types'

type Choice<K extends keyof ItemIn> = Exclude<ItemIn[K], null | undefined>

/** Form state of the "copy details" step; '' means "not set". */
export interface ItemDetails {
  format: Choice<'format'>
  status: Choice<'status'>
  condition: Choice<'condition'> | ''
  completeness: Choice<'completeness'> | ''
  play_status: Choice<'play_status'> | ''
  location_id: string
  owner_id: string
  acquired_on: string
  purchase_price: string
  notes: string
}

export function emptyDetails(): ItemDetails {
  return {
    format: 'physical',
    status: 'owned',
    condition: '',
    completeness: '',
    play_status: '',
    location_id: '',
    owner_id: '',
    acquired_on: '',
    purchase_price: '',
    notes: '',
  }
}

/** For bulk entry: keep where/whose/how, forget what is specific to one copy. */
export function nextDetails(previous: ItemDetails): ItemDetails {
  return { ...previous, purchase_price: '', notes: '' }
}

export function toItemIn(releaseId: string, d: ItemDetails): ItemIn {
  return {
    release_id: releaseId,
    format: d.format,
    status: d.status,
    condition: d.condition || null,
    completeness: d.completeness || null,
    play_status: d.play_status || null,
    location_id: d.location_id || null,
    owner_id: d.owner_id || null,
    acquired_on: d.acquired_on || null,
    purchase_price: d.purchase_price.trim().replace(',', '.') || null,
    notes: d.notes.trim(),
    title_override: '',
  }
}
