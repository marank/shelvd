/**
 * Every field an item can show, sort or filter by. Keys are paths – object and field –
 * the same everywhere (backend grouping, sorting, conditions; views; the URL):
 *   game.*                       the game itself (catalog, the same for everyone)
 *   release.*, platform.*, publisher.*   one edition of it (catalog)
 *   copy.*, location.*, owner.*, loan.*  your copy (this library only)
 * Game and release fields read from a release, copy fields from a copy: the detail column
 * can show a game's fields without any copy (upcoming games).
 */
import { Disc3, Gamepad2, Package, type LucideIcon } from '@lucide/vue'
import { useI18n } from 'vue-i18n'
import type { Item, Release } from '@/api/types'
import { formatReleaseDate } from './releaseDate'
import { platformPage, termPage, type TermKind, type TermRef } from './terms'

export type FieldLevel = 'work' | 'release' | 'item'

/** One icon and one name per level, used everywhere (picker, detail column, edit pages). */
export const LEVELS: { key: FieldLevel; icon: LucideIcon; scope: 'catalog' | 'library' }[] = [
  { key: 'item', icon: Package, scope: 'library' },
  { key: 'release', icon: Disc3, scope: 'catalog' },
  { key: 'work', icon: Gamepad2, scope: 'catalog' },
]

/** The objects a key starts with, and the level each belongs to. */
const OBJECTS = {
  game: 'work',
  release: 'release',
  platform: 'release',
  publisher: 'release',
  copy: 'item',
  location: 'item',
  owner: 'item',
  loan: 'item',
} as const satisfies Record<string, FieldLevel>
type FieldObject = keyof typeof OBJECTS
/** Objects that are a level themselves: their fields read without the object's name. */
const LEVEL_OBJECTS: FieldObject[] = ['game', 'release', 'copy']

type Kind = 'text' | 'code' | 'number' | 'money' | 'date' | 'choice' | 'hours' | 'percent'

interface FieldDef {
  kind?: Kind
  /** Raw value; arrays are joined. Empty → "". Copy fields get `item`. */
  get: (release: Release, item?: Item) => unknown
  /** Values are translated as choices.<choice>.<value> (labels of groups, too). */
  choice?: string
  /** Each value is a catalog term (or the platform) and links to its page (detail blocks). */
  link?: { kind: TermKind | 'platforms'; refs: (release: Release) => TermRef[] }
  /** What to sort by when it isn't the value itself (table header click). */
  sort?: (release: Release, item?: Item) => unknown
}

const place = (item: Item | undefined, kind: string) =>
  item?.location?.trail.filter((s) => s.kind === kind).at(-1)?.name
const today = () => new Date().toISOString().slice(0, 10)
const names = (terms: TermRef[]) => terms.map((term) => term.name)
/** A cached fact of the game (HowLongToBeat, OpenCritic …), if the source had one. */
const fact = (r: Release, source: string, name: string) => r.facts[source]?.values[name]

const ITEM_FIELDS = {
  'game.title': { get: (r, i) => i?.title ?? r.title },
  'game.franchises': {
    link: { kind: 'franchises', refs: (r) => r.franchises },
    get: (r) => names(r.franchises),
  },
  'game.series': { link: { kind: 'series', refs: (r) => r.series }, get: (r) => names(r.series) },
  'game.genres': { link: { kind: 'genres', refs: (r) => r.genres }, get: (r) => names(r.genres) },
  'game.developers': {
    link: { kind: 'companies', refs: (r) => r.developers },
    get: (r) => names(r.developers),
  },
  // How it's played: IGDB's English names, translated where we know them.
  'game.modes': { kind: 'choice', choice: 'game_mode', get: (r) => r.game_modes },
  'game.perspectives': { kind: 'choice', choice: 'perspective', get: (r) => r.perspectives },
  'game.languages': {
    kind: 'choice',
    choice: 'language',
    get: (r) => Object.keys(r.languages),
  },
  'game.first_release': { kind: 'date', get: (r) => r.first_release_date },
  'game.kind': { kind: 'choice', choice: 'media_type', get: (r) => r.platform.media_type },
  'game.time_main': { kind: 'hours', get: (r) => fact(r, 'hltb', 'main') },
  'game.time_extra': { kind: 'hours', get: (r) => fact(r, 'hltb', 'extra') },
  'game.time_complete': { kind: 'hours', get: (r) => fact(r, 'hltb', 'complete') },
  'game.critic_score': { kind: 'number', get: (r) => fact(r, 'opencritic', 'score') },
  'game.critic_recommended': {
    kind: 'percent',
    get: (r) => fact(r, 'opencritic', 'recommended'),
  },
  'release.edition': { get: (r) => r.edition },
  'release.region': { kind: 'code', choice: 'region', get: (r) => r.region.toUpperCase() },
  'release.year': { kind: 'number', get: (r) => r.year },
  'release.date': { kind: 'date', get: (r) => r, sort: (r) => r.sort_date },
  'release.number': {
    kind: 'number',
    get: (r) => (r.release_number ? `#${r.release_number}` : ''),
    sort: (r) => r.release_number,
  },
  'release.product_code': { kind: 'code', get: (r) => r.product_code },
  'release.barcodes': { kind: 'code', get: (r) => r.barcodes },
  'release.age_rating': { get: (r) => r.age_rating },
  'release.players_offline': { kind: 'number', get: (r) => r.players_offline },
  'release.players_online': { kind: 'number', get: (r) => r.players_online },
  'release.developers': {
    link: { kind: 'companies', refs: (r) => r.release_developers },
    get: (r) => names(r.release_developers),
  },
  'platform.name': {
    link: { kind: 'platforms', refs: (r) => [r.platform] },
    get: (r) => r.platform.name,
  },
  'platform.manufacturer': { get: (r) => r.platform.manufacturer },
  'platform.year': { kind: 'number', get: (r) => r.platform.release_year },
  'publisher.name': {
    link: { kind: 'companies', refs: (r) => (r.publisher ? [r.publisher] : []) },
    get: (r) => r.publisher?.name,
  },
  'copy.status': { kind: 'choice', choice: 'status', get: (_, i) => i?.status },
  'copy.format': { kind: 'choice', choice: 'format', get: (_, i) => i?.format },
  'copy.condition': { kind: 'choice', choice: 'condition', get: (_, i) => i?.condition },
  'copy.completeness': {
    kind: 'choice',
    choice: 'completeness',
    get: (_, i) => i?.completeness,
  },
  'copy.progress': { kind: 'choice', choice: 'play_status', get: (_, i) => i?.play_status },
  'copy.value': { kind: 'money', get: (_, i) => i?.current_value },
  'copy.price': { kind: 'money', get: (_, i) => i?.purchase_price },
  'copy.acquired': { kind: 'date', get: (_, i) => i?.acquired_on },
  'copy.added': { kind: 'date', get: (_, i) => i?.created_at.slice(0, 10) },
  'copy.tags': { get: (_, i) => i?.tags.map((t) => `#${t}`) },
  'copy.notes': { get: (_, i) => i?.notes },
  'location.path': { get: (_, i) => i?.location?.path },
  'location.name': { get: (_, i) => i?.location?.name },
  'location.kind': {
    kind: 'choice',
    choice: 'location_kind',
    get: (_, i) => i?.location?.trail.at(-1)?.kind,
  },
  'location.room': { get: (_, i) => i?.location?.trail[0]?.name },
  'location.shelf': { get: (_, i) => place(i, 'shelf') },
  'location.box': { get: (_, i) => place(i, 'box') },
  'owner.name': { get: (_, i) => i?.owner?.name },
  'loan.to': { get: (_, i) => i?.active_loan?.borrower?.name },
  'loan.since': { kind: 'date', get: (_, i) => i?.active_loan?.lent_on },
  'loan.due': { kind: 'date', get: (_, i) => i?.active_loan?.due_on },
  'loan.overdue': {
    kind: 'choice',
    choice: 'loan_overdue',
    get: (_, i) => {
      const due = i?.active_loan?.due_on
      return due && due < today() ? 'yes' : ''
    },
  },
} satisfies Record<string, FieldDef>

export type ItemFieldKey = keyof typeof ITEM_FIELDS
export const FIELD_KEYS = Object.keys(ITEM_FIELDS) as ItemFieldKey[]

const DEFS = ITEM_FIELDS as Record<ItemFieldKey, FieldDef>
const objectOf = (key: string) => key.split('.')[0] as FieldObject
export const fieldLevel = (key: ItemFieldKey): FieldLevel => OBJECTS[objectOf(key)]
/** Monospace + tabular: codes, numbers, money, dates. */
export const isMono = (key: ItemFieldKey) => !['text', 'choice'].includes(DEFS[key].kind ?? 'text')
export const isNumeric = (key: ItemFieldKey) =>
  ['money', 'hours', 'percent'].includes(DEFS[key].kind ?? '')
/** A term field's values as links to their pages; null for other fields. */
export function fieldLinks(key: ItemFieldKey, release: Release) {
  const link = DEFS[key].link
  if (!link) return null
  return link.refs(release).map((ref) => ({
    ...ref,
    to: link.kind === 'platforms' ? platformPage(ref.id) : termPage(link.kind, ref.id),
  }))
}
export const fieldKind = (key: ItemFieldKey): Kind => DEFS[key].kind ?? 'text'
/** Choice namespace of a field's values (also for grouping keys), if any. */
export const fieldChoice = (key: string) =>
  key in DEFS ? DEFS[key as ItemFieldKey].choice : undefined

/** The objects of one level and their fields, in registry order (for pickers). */
export function fieldsOf(level: FieldLevel, keys: readonly ItemFieldKey[] = FIELD_KEYS) {
  const groups = new Map<FieldObject, ItemFieldKey[]>()
  for (const key of keys) {
    if (fieldLevel(key) !== level) continue
    groups.set(objectOf(key), [...(groups.get(objectOf(key)) ?? []), key])
  }
  return [...groups].map(([object, fields]) => ({
    object,
    /** Fields of the level itself are shown loose, other objects as a labelled cluster. */
    loose: LEVEL_OBJECTS.includes(object),
    fields,
  }))
}

/** Each object's main field reads as just the object: "Plattform", not "Plattform › Name". */
const PRIMARY: Partial<Record<FieldObject, string>> = {
  platform: 'platform.name',
  publisher: 'publisher.name',
  owner: 'owner.name',
  location: 'location.path',
}

/**
 * Labels: "Serie" for the level's own fields, "Ort › Typ" for an object's, just "Ort" for
 * an object's main field. `matches` finds fields by any of these words, also typed as a
 * path ("ort.ty", "ausgabe.nummer").
 */
export function useFieldLabel() {
  const { t } = useI18n()
  const objectLabel = (object: FieldObject) => t(`itemObjects.${object}`)
  function label(key: string): string {
    const object = objectOf(key)
    if (LEVEL_OBJECTS.includes(object)) return t(`itemFields.${key}`)
    if (PRIMARY[object] === key) return objectLabel(object)
    return `${objectLabel(object)} › ${t(`itemFields.${key}`)}`
  }
  /** Just the field's own name, without its object ("Typ"). */
  const short = (key: string) => t(`itemFields.${key}`)
  function matches(key: string, query: string): boolean {
    const q = query.trim().toLowerCase()
    if (!q || key.includes(q)) return true
    const object = objectOf(key)
    const level = OBJECTS[object]
    const levelObject = LEVEL_OBJECTS.find((o) => OBJECTS[o] === level)!
    const words = [objectLabel(levelObject), objectLabel(object), t(`itemFields.${key}`), key].map(
      (w) => w.toLowerCase(),
    )
    const parts = q.split(/\s*[.›>]\s*/).filter(Boolean)
    if (parts.length > 1) {
      // Each typed part starts a later word: "ort.ty" → Ort › Typ.
      let from = 0
      return parts.every((part) => {
        const at = words.findIndex((w, i) => i >= from && w.startsWith(part))
        from = at + 1
        return at >= 0
      })
    }
    return label(key).toLowerCase().includes(q) || words.some((w) => w.startsWith(q))
  }
  return Object.assign(label, { short, matches, object: objectLabel })
}

/** Where a view shows fields: its three layouts and the detail column. */
export const PRESENTATIONS = ['grid', 'list', 'table', 'detail'] as const
export type Presentation = (typeof PRESENTATIONS)[number]
export type ViewFields = Record<Presentation, ItemFieldKey[]>

/** What each presentation shows until a view picks its own fields. In the detail column
 * every field appears in its level's block: game, release, or on each copy. */
export const DEFAULT_FIELDS: ViewFields = {
  grid: ['release.year', 'publisher.name'],
  list: ['release.year', 'publisher.name', 'location.path'],
  table: [
    'platform.name',
    'release.region',
    'release.year',
    'publisher.name',
    'location.path',
    'owner.name',
    'copy.value',
    'copy.status',
  ],
  detail: [
    'game.time_main',
    'game.critic_score',
    'game.developers',
    'game.genres',
    'game.series',
    'game.first_release',
    'publisher.name',
    'release.number',
    'release.product_code',
    'location.path',
    'owner.name',
    'copy.value',
    'copy.completeness',
    'copy.condition',
    'copy.progress',
    'copy.tags',
    'copy.notes',
  ],
}

/** Stored keys → known fields (anything else is skipped). */
export function knownFields(keys: readonly string[]): ItemFieldKey[] {
  return keys.filter((k): k is ItemFieldKey => k in ITEM_FIELDS)
}

/** A view's stored fields → every presentation's known keys ([] = defaults). */
export function viewFields(stored: Partial<Record<string, readonly string[]>> | undefined) {
  return Object.fromEntries(
    PRESENTATIONS.map((p) => [p, knownFields(stored?.[p] ?? [])]),
  ) as ViewFields
}

/** The fields a presentation shows: the view's own, else the defaults. */
export const shownFields = (fields: ViewFields, presentation: Presentation) =>
  fields[presentation].length ? fields[presentation] : DEFAULT_FIELDS[presentation]

/** Formats fields as text; "" when empty. `parts` keeps list values apart (for links). */
/** "Bird view / Isometric" → "bird_view_isometric": a value as a message key. */
const choiceKey = (value: string) =>
  value
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/^_|_$/g, '')

/** A choice's label (choices.<choice>.<key>); values we have no label for read as they are
 * (IGDB's names of new game modes or languages). */
export function useChoiceLabel() {
  const i18n = useI18n()
  return (choice: string, value: string) => {
    const key = `choices.${choice}.${choiceKey(value)}`
    return i18n.te(key) ? i18n.t(key) : value
  }
}

export function useFieldValue() {
  const { t, n, d, locale } = useI18n()
  const choiceLabel = useChoiceLabel()
  function parts(key: ItemFieldKey, release: Release, item?: Item): string[] {
    const raw = DEFS[key].get(release, item)
    if (raw === null || raw === undefined || raw === '') return []
    return (Array.isArray(raw) ? raw : [raw]).map((v) => format(key, v)).filter(Boolean)
  }
  function format(key: ItemFieldKey, raw: unknown): string {
    const def = DEFS[key]
    switch (def.kind) {
      case 'choice':
        return choiceLabel(def.choice!, String(raw))
      case 'money':
        return n(Number(raw), 'currency')
      case 'hours':
        return `${n(Number(raw), { maximumFractionDigits: 1 })} h`
      case 'percent':
        return `${n(Math.round(Number(raw)))} %`
      case 'date':
        return typeof raw === 'string'
          ? d(new Date(raw), 'short')
          : formatReleaseDate(raw as Release, locale.value, t('dates.tba'))
      case 'code':
      case 'number':
      case 'text':
      case undefined:
        return String(raw)
    }
  }
  /** One field of a copy, as one line of text. */
  const value = (key: ItemFieldKey, item: Item) => parts(key, item.release, item).join(', ')
  return Object.assign(value, { parts })
}

/** Leading articles don't count when sorting titles ("The Witcher 3" sorts under W). */
const ARTICLES = /^(the|a|an|der|die|das|ein|eine|le|la|les|el|los|las)\s+/i

/** Compares items by a field the way a person expects: numbers and money as numbers,
 * dates by date, text by its shown words; empty values always last. */
export function useFieldSort() {
  const value = useFieldValue()
  const collator = new Intl.Collator(undefined, { numeric: true, sensitivity: 'base' })
  function key(field: ItemFieldKey, item: Item): string | number | null {
    if (field === 'game.title') return item.title.trim().replace(ARTICLES, '')
    const def = DEFS[field]
    const raw = (def.sort ?? def.get)(item.release, item)
    if (raw === null || raw === undefined || raw === '') return null
    if (['money', 'number', 'hours', 'percent'].includes(def.kind ?? '')) return Number(raw)
    if (def.kind === 'date' && typeof raw === 'string') return raw
    return value(field, item) || null
  }
  return (items: Item[], field: ItemFieldKey, desc: boolean): Item[] => {
    const keyed = items.map((item) => ({ item, key: key(field, item) }))
    keyed.sort((a, b) => {
      if (a.key === null || b.key === null) return a.key === b.key ? 0 : a.key === null ? 1 : -1
      const order =
        typeof a.key === 'number' && typeof b.key === 'number'
          ? a.key - b.key
          : collator.compare(String(a.key), String(b.key))
      return desc ? -order : order
    })
    return keyed.map((k) => k.item)
  }
}

/** A view's sort: up to five levels, any field (shown or not). */
export interface SortLevel {
  key: ItemFieldKey
  desc: boolean
}
export const MAX_SORT_LEVELS = 5
export const DEFAULT_SORT = 'game.title'

/** "location.box,-release.number" → levels; unknown keys are skipped. The plain default
 * (by title – titles break every tie anyway) reads as no levels. */
export function parseSort(spec: string | undefined): SortLevel[] {
  if (!spec || spec === DEFAULT_SORT) return []
  return spec
    .split(',')
    .map((part) => part.trim())
    .filter(Boolean)
    .map((part) => ({ key: part.replace(/^-/, ''), desc: part.startsWith('-') }))
    .filter((l): l is SortLevel => l.key in ITEM_FIELDS)
    .slice(0, MAX_SORT_LEVELS)
}

export const formatSort = (levels: SortLevel[]) =>
  levels.map((l) => `${l.desc ? '-' : ''}${l.key}`).join(',') || DEFAULT_SORT
