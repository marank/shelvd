/**
 * A view's filter conditions, mirroring the backend's `collection/selectors/conditions.py`:
 * field · operator · value, stored as short text ("game.title~A*", "location.box?",
 * "release.year>=2020").
 */
import { GROUP_FIELDS, type GroupField } from '@/api/types'
import { FIELD_KEYS, fieldKind, type ItemFieldKey } from './itemFields'

const OPS = ['in', 'not_in', 'match', 'not_match', 'set', 'empty', 'gte', 'lte', 'between'] as const
export type Op = (typeof OPS)[number]

const TOKENS: Record<Op, string> = {
  in: '=',
  not_in: '!=',
  match: '~',
  not_match: '!~',
  set: '?',
  empty: '!?',
  gte: '>=',
  lte: '<=',
  between: '><',
}
const PATTERN = /^([a-z]+\.[a-z_]+)(!\?|\?|!~|~|!=|>=|<=|><|=)(.*)$/s

export interface Condition {
  field: ItemFieldKey
  op: Op
  /** Group keys for in / not_in. */
  values: string[]
  /** Pattern, or the bound(s) of a comparison. */
  text: string
  high: string
}

/** The tree field a condition's values come from, if the field groups. */
export function groupFieldOf(field: ItemFieldKey): GroupField | null {
  return GROUP_FIELDS.includes(field as GroupField) ? (field as GroupField) : null
}

const RANGE_KINDS = ['number', 'money', 'date', 'hours', 'percent']
export const isDateField = (field: ItemFieldKey) => fieldKind(field) === 'date'

/** Operators that make sense for a field, the most useful first. */
export function opsFor(field: ItemFieldKey): Op[] {
  const kind = fieldKind(field)
  const ranged = RANGE_KINDS.includes(kind)
  return [
    ...(groupFieldOf(field) ? (['in', 'not_in'] as const) : []),
    ...(kind !== 'choice' && !ranged ? (['match', 'not_match'] as const) : []),
    ...(ranged ? (['gte', 'lte', 'between'] as const) : []),
    'set',
    'empty',
  ]
}

export function newCondition(field: ItemFieldKey = 'game.title'): Condition {
  return { field, op: opsFor(field)[0]!, values: [], text: '', high: '' }
}

function parseCondition(raw: string): Condition | null {
  const match = PATTERN.exec(raw.trim())
  if (!match) return null
  const [, field, token, value = ''] = match
  const op = (Object.keys(TOKENS) as Op[]).find((o) => TOKENS[o] === token)
  if (!op || !FIELD_KEYS.includes(field as ItemFieldKey)) return null
  const condition = newCondition(field as ItemFieldKey)
  condition.op = op
  if (op === 'in' || op === 'not_in') condition.values = value.split('|').filter(Boolean)
  else if (op === 'between') [condition.text = '', condition.high = ''] = value.split('..')
  else condition.text = value
  return condition
}

/** Text for the API, or null while the condition is still incomplete. */
function formatCondition(c: Condition): string | null {
  const head = `${c.field}${TOKENS[c.op]}`
  switch (c.op) {
    case 'in':
    case 'not_in':
      return c.values.length ? head + c.values.join('|') : null
    case 'set':
    case 'empty':
      return head
    case 'between':
      return c.text.trim() && c.high.trim() ? `${head}${c.text.trim()}..${c.high.trim()}` : null
    case 'match':
    case 'not_match':
    case 'gte':
    case 'lte':
      return c.text.trim() ? head + c.text.trim() : null
  }
}

export const formatConditions = (conditions: Condition[]) =>
  conditions.map(formatCondition).filter((c): c is string => c !== null)

export const parseConditions = (raw: readonly string[]) =>
  raw.map(parseCondition).filter((c): c is Condition => c !== null)
