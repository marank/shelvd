import { computed, watch } from 'vue'
import { useRoute, useRouter, type LocationQueryRaw } from 'vue-router'
import { GROUP_FIELDS, type GroupField, type Overview } from '@/api/types'
import {
  PRESENTATIONS,
  formatSort,
  knownFields,
  parseSort,
  viewFields,
  type SortLevel,
  type ViewFields,
} from '@/lib/itemFields'
import { useOverviews } from './useOverviews'
import { useUiStore } from '@/stores/ui'

export type Layout = 'grid' | 'list' | 'table'

/** Clears unsaved field choices from the URL. */
export const NO_FIELD_CHANGES = Object.fromEntries(PRESENTATIONS.map((p) => [`f_${p}`, undefined]))
const LAYOUTS: Layout[] = ['grid', 'list', 'table']

function list(value: unknown): string[] {
  if (Array.isArray(value)) return value.filter((v): v is string => typeof v === 'string')
  return typeof value === 'string' && value ? [value] : []
}

function one(value: unknown): string | undefined {
  return list(value)[0]
}

/**
 * The explorer's state lives in the URL, so every view, folder and search can be
 * bookmarked, shared and navigated with back/forward:
 *   v=<overview id>  g=platform,publisher (unsaved nesting)  p=<group key> (one per level)
 *   s=copy.added (unsaved section headings; "," = none)
 *   q=<search>  sort=location.box,-release.number  layout=table  item=<selected item, detail column>
 *   f_table=release.year,location.box (unsaved fields per grid/list/table/detail; "," = the defaults)
 */
export function useExplorerState() {
  const route = useRoute()
  const router = useRouter()
  const libraryId = computed(() => String(route.params.libraryId ?? ''))
  const overviews = useOverviews(libraryId)

  const overview = computed<Overview | undefined>(() => {
    const all = overviews.data.value ?? []
    return all.find((o) => o.id === one(route.query.v)) ?? all[0]
  })
  // Remembered for pages outside the explorer (their detail fields, the sidebar).
  const ui = useUiStore()
  watch(
    overview,
    (view) => {
      if (view && libraryId.value) ui.lastView = { ...ui.lastView, [libraryId.value]: view.id }
    },
    { immediate: true },
  )

  const groupOverride = computed(() => {
    const raw = one(route.query.g)
    if (raw === undefined) return undefined
    return raw.split(',').filter((f): f is GroupField => GROUP_FIELDS.includes(f as GroupField))
  })
  const groupBy = computed<GroupField[]>(
    () => groupOverride.value ?? ((overview.value?.group_by ?? []) as GroupField[]),
  )
  /** The field whose groups head sections of the item list; '' = one plain list. */
  const section = computed<GroupField | ''>(() => {
    const raw = one(route.query.s) ?? overview.value?.section ?? ''
    return GROUP_FIELDS.includes(raw as GroupField) ? (raw as GroupField) : ''
  })
  const path = computed(() => list(route.query.p).slice(0, groupBy.value.length))
  const query = computed(() => one(route.query.q) ?? '')
  /** Sort levels ("location.box,-release.number"). */
  const sort = computed<SortLevel[]>(() => parseSort(one(route.query.sort) ?? overview.value?.sort))
  const layout = computed<Layout>(() => {
    const value = one(route.query.layout) ?? overview.value?.layout
    return LAYOUTS.includes(value as Layout) ? (value as Layout) : 'grid'
  })

  const itemId = computed(() => one(route.query.item))

  /** Fields per presentation: the view's, with unsaved changes from the URL on top. */
  const savedFields = computed(() => viewFields(overview.value?.fields))
  const fields = computed<ViewFields>(() => {
    const result = { ...savedFields.value }
    for (const p of PRESENTATIONS) {
      const raw = one(route.query[`f_${p}`])
      if (raw !== undefined) result[p] = knownFields(raw.split(','))
    }
    return result
  })
  const fieldsChanged = computed(() =>
    PRESENTATIONS.some((p) => fields.value[p].join(',') !== savedFields.value[p].join(',')),
  )

  /** One filter per opened folder level. */
  const filters = computed(() => path.value.map((key, i) => `${groupBy.value[i]}:${key}`))
  /** The view's own conditions; they apply to tree and items alike. */
  const where = computed(() => overview.value?.filters ?? [])
  const match = computed(() => overview.value?.match ?? 'all')

  const dirty = computed(() => {
    const o = overview.value
    if (!o) return groupBy.value.length > 0 || !!section.value || fieldsChanged.value
    return (
      groupBy.value.join(',') !== o.group_by.join(',') ||
      section.value !== o.section ||
      formatSort(sort.value) !== formatSort(parseSort(o.sort)) ||
      layout.value !== o.layout ||
      fieldsChanged.value
    )
  })

  function navigate(patch: LocationQueryRaw, mode: 'push' | 'replace' = 'push') {
    const next: LocationQueryRaw = { ...route.query, ...patch }
    for (const [key, value] of Object.entries(next)) {
      if (
        value === undefined ||
        value === null ||
        value === '' ||
        (Array.isArray(value) && !value.length)
      )
        delete next[key]
    }
    return router[mode]({ name: 'explorer', params: { libraryId: libraryId.value }, query: next })
  }

  return {
    libraryId,
    overviews,
    overview,
    groupBy,
    section,
    path,
    query,
    sort,
    layout,
    fields,
    filters,
    where,
    match,
    dirty,
    itemId,
    navigate,
    openPath: (keys: string[]) => navigate({ p: keys }),
    /** Select an item for the detail column; replace, so arrow keys don't flood history. */
    selectItem: (id: string | undefined) => navigate({ item: id }, 'replace'),
    selectOverview: (id: string) =>
      navigate({
        v: id,
        g: undefined,
        s: undefined,
        p: undefined,
        sort: undefined,
        layout: undefined,
        ...NO_FIELD_CHANGES,
      }),
    setGroupBy: (fields: GroupField[]) =>
      navigate({ g: fields.join(',') || ',', p: undefined }, 'replace'),
    setSection: (field: GroupField | '') =>
      navigate(
        { s: field === (overview.value?.section ?? '') ? undefined : field || ',' },
        'replace',
      ),
    setSearch: (q: string) => navigate({ q: q || undefined }, 'replace'),
    setSort: (levels: SortLevel[]) => navigate({ sort: formatSort(levels) }, 'replace'),
    setLayout: (value: Layout) => navigate({ layout: value }, 'replace'),
    /** Only what differs from the saved view goes into the URL. */
    setFields: (next: ViewFields) =>
      navigate(
        Object.fromEntries(
          PRESENTATIONS.map((p) => [
            `f_${p}`,
            next[p].join(',') === savedFields.value[p].join(',')
              ? undefined
              : next[p].join(',') || ',',
          ]),
        ),
        'replace',
      ),
  }
}
