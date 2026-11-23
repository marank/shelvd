<script setup lang="ts">
import { onKeyStroke, useElementSize, useIntersectionObserver, useMediaQuery } from '@vueuse/core'
import { ChevronRight, SearchX } from '@lucide/vue'
import { computed, defineAsyncComponent, nextTick, ref, useTemplateRef, watchEffect } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { toast } from 'vue-sonner'
import { Button } from '@/components/ui/button'
import {
  Empty,
  EmptyContent,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from '@/components/ui/empty'
import { Skeleton } from '@/components/ui/skeleton'
import { Spinner } from '@/components/ui/spinner'
import type { GroupNode, Item, Section } from '@/api/types'
import { canEdit, useLibrary } from '@/features/library/composables/useLibraries'
import { usePlatforms } from '@/features/library/composables/useReference'
import { useGroupLabel } from '@/lib/labels'
import { useUiStore } from '@/stores/ui'
import DetailPane from '../components/DetailPane.vue'
import FolderGrid from '../components/FolderGrid.vue'
import ItemCard from '../components/ItemCard.vue'
import ItemRows from '../components/ItemRows.vue'
import ViewControls from '../components/ViewControls.vue'
import ViewMenu from '../components/ViewMenu.vue'
import { NO_FIELD_CHANGES, useExplorerState } from '../composables/useExplorerState'
import { justify } from '../composables/justify'
import {
  PRESENTATIONS,
  formatSort,
  shownFields as fieldsFor,
  useFieldSort,
  type ItemFieldKey,
  type SortLevel,
  useFieldLabel,
} from '@/lib/itemFields'
import { useItems, useTree } from '../composables/useItems'
import { useSaveOverview } from '../composables/useOverviews'

const DeleteViewDialog = defineAsyncComponent(() => import('../components/DeleteViewDialog.vue'))

const { t, n } = useI18n()
const router = useRouter()
const ui = useUiStore()
const label = useGroupLabel()
const fieldLabel = useFieldLabel()
const state = useExplorerState()
const library = useLibrary(state.libraryId)
const platforms = usePlatforms()
const saveOverview = useSaveOverview(state.libraryId)
const desktop = useMediaQuery('(min-width: 1024px)')

const tree = useTree(state.libraryId, () => ({
  groupBy: state.groupBy.value,
  q: state.query.value,
  filters: [],
  where: state.where.value,
  match: state.match.value,
}))
const items = useItems(state.libraryId, () => ({
  q: state.query.value,
  filters: state.filters.value,
  where: state.where.value,
  match: state.match.value,
  sort: formatSort(state.sort.value),
  section: state.section.value,
}))

const loaded = computed(() => items.data.value?.pages.flatMap((page) => page.items) ?? [])

// --- table column sort: only while the page is open (not in the URL, never saved) ------
const columnSort = ref<SortLevel | null>(null)
const sortItems = useFieldSort()
const tableSorted = computed(() => state.layout.value === 'table' && !!columnSort.value)
// --- sections: the list in groups under collapsible headings ---------------------------
interface Group {
  /** Unique per list; the section's key, or '' without sections. */
  key: string
  section: Section | null
  /** Its loaded rows, in the order they're shown. */
  items: Item[]
  open: boolean
}
const sections = computed<Section[]>(() =>
  state.section.value ? (items.data.value?.pages[0]?.sections ?? []) : [],
)
const collapseKey = computed(() => `${state.libraryId.value}|${state.section.value}`)
const collapsed = computed(() => new Set(ui.collapsed[collapseKey.value] ?? []))
function setCollapsed(keys: string[]) {
  const next = { ...ui.collapsed }
  if (keys.length) next[collapseKey.value] = keys
  else delete next[collapseKey.value]
  ui.collapsed = next
}
function toggleSection(key: string) {
  const keys = new Set(collapsed.value)
  if (keys.has(key)) keys.delete(key)
  else keys.add(key)
  setCollapsed([...keys])
}
const allCollapsed = computed(
  () => sections.value.length > 0 && sections.value.every((s) => collapsed.value.has(s.key)),
)
function toggleAll() {
  setCollapsed(allCollapsed.value ? [] : sections.value.map((s) => s.key))
}

function ordered(list: Item[]): Item[] {
  return tableSorted.value ? sortItems(list, columnSort.value!.key, columnSort.value!.desc) : list
}
const groups = computed<Group[]>(() => {
  if (!sections.value.length)
    return [{ key: '', section: null, items: ordered(loaded.value), open: true }]
  return sections.value.map((section) => ({
    key: section.key,
    section,
    items: ordered(loaded.value.slice(section.start, section.start + section.count)),
    open: !collapsed.value.has(section.key),
  }))
})
/** Items in the order they're shown (and arrow keys walk); folded-in sections don't count. */
const shown = computed(() => groups.value.flatMap((g) => (g.open ? g.items : [])))
/** Whether an open section still has rows to load (folded-in ones need none). */
const wantMore = computed(
  () =>
    items.hasNextPage.value &&
    (!sections.value.length ||
      sections.value.some(
        (s) => !collapsed.value.has(s.key) && s.start + s.count > loaded.value.length,
      )),
)
/** Header click: ascending → descending → the view's own order. */
function sortBy(key: ItemFieldKey) {
  const current = columnSort.value
  if (current?.key !== key) columnSort.value = { key, desc: false }
  else if (!current.desc) columnSort.value = { key, desc: true }
  else columnSort.value = null
}
// Sorting only some of the items would be wrong: fetch the rest while a column sort is on.
watchEffect(() => {
  if (tableSorted.value && items.hasNextPage.value && !items.isFetchingNextPage.value) {
    void items.fetchNextPage()
  }
})
const total = computed(() => items.data.value?.pages[0]?.count ?? 0)

/** The nodes along the open path; the last one's children are shown as folders. */
const trail = computed(() => {
  const nodes: GroupNode[] = []
  let level = tree.data.value?.nodes ?? []
  for (const key of state.path.value) {
    const node = level.find((n) => n.key === key)
    if (!node) break
    nodes.push(node)
    level = node.children
  }
  return { nodes, children: level }
})
const viewName = computed(() => state.overview.value?.name ?? t('nav.allItems'))
/** The open folder, else the view itself. */
const title = computed(() => {
  const node = trail.value.nodes[trail.value.nodes.length - 1]
  return node && state.path.value.length ? label(node.field, node.key, node.label) : viewName.value
})
const folders = computed(() =>
  state.path.value.length < state.groupBy.value.length ? trail.value.children : [],
)

const sentinel = useTemplateRef<HTMLElement>('sentinel')
useIntersectionObserver(sentinel, ([entry]) => {
  if (entry?.isIntersecting && wantMore.value && !items.isFetchingNextPage.value) {
    void items.fetchNextPage()
  }
})

// --- saved views ----------------------------------------------------------------------
async function saveView() {
  const overview = state.overview.value
  if (!overview) {
    void router.push(saveAsNewTo.value)
    return
  }
  await saveOverview.update.mutateAsync({
    id: overview.id,
    body: {
      group_by: state.groupBy.value,
      section: state.section.value,
      sort: formatSort(state.sort.value),
      layout: state.layout.value,
      fields: state.fields.value,
    },
  })
  toast.success(t('explorer.viewSaved'))
  void state.navigate(
    { g: undefined, s: undefined, sort: undefined, layout: undefined, ...NO_FIELD_CHANGES },
    'replace',
  )
}

/** The view's own fields for this layout, else its defaults. */
const shownFields = computed(() => fieldsFor(state.fields.value, state.layout.value))

const saveAsNewTo = computed(() => ({
  name: 'overview-new',
  params: { libraryId: state.libraryId.value },
  query: {
    g: state.groupBy.value.join(','),
    s: state.section.value || undefined,
    sort: formatSort(state.sort.value),
    layout: state.layout.value,
    ...Object.fromEntries(
      PRESENTATIONS.map((p) => [`f_${p}`, state.fields.value[p].join(',') || undefined]),
    ),
  },
}))
const editTo = computed(() =>
  state.overview.value
    ? {
        name: 'overview-edit',
        params: { libraryId: state.libraryId.value, overviewId: state.overview.value.id },
      }
    : undefined,
)

async function duplicateView() {
  const overview = state.overview.value
  if (!overview) return
  const copy = await saveOverview.create.mutateAsync({
    name: `${overview.name} ${t('explorer.copySuffix')}`,
    group_by: overview.group_by,
    section: overview.section,
    filters: overview.filters,
    match: overview.match,
    sort: overview.sort,
    layout: overview.layout,
    fields: overview.fields,
    position: (state.overviews.data.value?.length ?? 0) + 1,
  })
  void state.selectOverview(copy.id)
}

const deleting = ref(false)
async function deleteView() {
  const overview = state.overview.value
  if (!overview) return
  await saveOverview.remove.mutateAsync(overview.id)
  deleting.value = false
  void state.navigate({ v: undefined, g: undefined, p: undefined })
}

// --- items and the detail column -------------------------------------------------------
const paneOpen = computed(() => ui.detailPane && desktop.value && !!state.itemId.value)

/** With the detail column on, a click selects; otherwise it opens the copy's page. */
function openItem(item: Item) {
  if (ui.detailPane && desktop.value) {
    void state.selectItem(item.id)
    return
  }
  void router.push({ name: 'item', params: { itemId: item.id } })
}

function isTyping(event: KeyboardEvent): boolean {
  const target = event.target as HTMLElement | null
  return (
    !!target &&
    (['INPUT', 'TEXTAREA', 'SELECT'].includes(target.tagName) || target.isContentEditable)
  )
}

function step(delta: number) {
  const list = shown.value
  if (!list.length) return
  const index = list.findIndex((i) => i.id === state.itemId.value)
  const next = list[Math.min(list.length - 1, Math.max(0, index + delta))]
  if (!next) return
  void state.selectItem(next.id)
  void nextTick(() =>
    document.querySelector(`[data-item-id="${next.id}"]`)?.scrollIntoView({ block: 'nearest' }),
  )
}

// Keyboard: arrows move the selection while the detail column is open, Esc closes it.
onKeyStroke(['ArrowDown', 'ArrowRight', 'ArrowUp', 'ArrowLeft', 'Escape'], (event) => {
  if (
    !paneOpen.value ||
    isTyping(event) ||
    document.querySelector('[role="dialog"], [role="menu"], [role="listbox"]')
  )
    return
  event.preventDefault()
  if (event.key === 'Escape') void state.selectItem(undefined)
  else step(event.key === 'ArrowDown' || event.key === 'ArrowRight' ? 1 : -1)
})

function setDetailPane(on: boolean) {
  ui.detailPane = on
  if (on && !state.itemId.value && loaded.value[0]) void state.selectItem(loaded.value[0].id)
  if (!on) void state.selectItem(undefined)
}

const list = useTemplateRef<HTMLElement>('list')
const { width: gridWidth } = useElementSize(list)
/** Card widths of each section's justified rows (see composables/justify.ts). */
const cardWidths = computed(() =>
  groups.value.map((group) => {
    const aspects = group.items.map((item) => item.cover_aspect ?? 5 / 7)
    // Before the list is measured (and in tests), lay out as if it were wide enough.
    const width = gridWidth.value || aspects.length * rowHeight.value
    return justify(aspects, { width, rowHeight: rowHeight.value, gap: 8, padding: 12 })
  }),
)

/** Target cover height per row for S/M/L; the phone gets a bit less. */
const rowHeight = computed(() => {
  const base = { s: 140, m: 200, l: 270 }[ui.gridSize]
  return desktop.value ? base : Math.round(base * 0.8)
})

/** Sum of the collector's values of everything shown (the open folder, or all). */
const totalValue = computed(() => {
  const node = trail.value.nodes[trail.value.nodes.length - 1]
  const raw = node && state.path.value.length ? node.value : tree.data.value?.total_value
  return Number(raw ?? 0)
})

const statusLine = computed(() => {
  const parts = [t('common.items', { n: total.value }, total.value)]
  if (totalValue.value > 0) {
    parts.push(t('common.value', { value: n(totalValue.value, 'currency') }))
  }
  if (state.groupBy.value.length) {
    parts.push(state.groupBy.value.map((f) => fieldLabel(f)).join(' · '))
  }
  if (state.section.value) {
    parts.push(`${t('explorer.sections')}: ${fieldLabel(state.section.value)}`)
  }
  if (state.query.value) parts.push(`"${state.query.value}"`)
  return parts.join('  ·  ')
})
</script>

<template>
  <div class="flex min-h-0 flex-1">
    <div class="flex min-w-0 flex-1 flex-col">
      <!-- Head and content scroll together: on the phone only the topbar stays put. -->
      <div class="flex-1 overflow-y-auto" data-testid="explorer-scroll">
        <header
          class="flex flex-wrap items-end gap-x-4 gap-y-3 border-b px-4 pt-4 pb-3 md:px-6 md:pt-5 md:pb-4"
        >
          <div class="min-w-0 flex-1 basis-full sm:basis-auto">
            <!-- Where this folder sits: library › view › parent folders. -->
            <nav
              :aria-label="t('explorer.path')"
              class="flex min-w-0 items-center gap-1 font-mono text-[11px] tracking-wider text-muted-foreground uppercase"
            >
              <span class="max-w-[40%] shrink-0 truncate">{{ library.data.value?.name }}</span>
              <template v-if="state.path.value.length">
                <ChevronRight class="size-3 shrink-0" />
                <button
                  type="button"
                  class="min-w-0 truncate uppercase hover:text-foreground"
                  data-testid="crumb-root"
                  @click="state.openPath([])"
                >
                  {{ viewName }}
                </button>
                <template v-for="(node, index) in trail.nodes.slice(0, -1)" :key="node.key">
                  <ChevronRight class="size-3 shrink-0" />
                  <button
                    type="button"
                    class="min-w-0 truncate uppercase hover:text-foreground"
                    @click="state.openPath(state.path.value.slice(0, index + 1))"
                  >
                    {{ label(node.field, node.key, node.label) }}
                  </button>
                </template>
              </template>
              <ChevronRight class="size-3 shrink-0" />
            </nav>
            <h1 class="flex min-w-0 items-baseline gap-2.5" data-testid="explorer-title">
              <span class="truncate text-xl font-semibold tracking-tight md:text-2xl">
                {{ title }}
              </span>
              <span class="tabular shrink-0 font-mono text-[11px] text-muted-foreground">
                {{ n(total) }}
              </span>
            </h1>
          </div>
          <!-- View buttons and the view's ⋮ menu stay together on the right. -->
          <div class="ml-auto flex items-center gap-1.5">
            <ViewControls
              :sort="state.sort.value"
              :layout="state.layout.value"
              :section="state.section.value"
              :all-collapsed="sections.length > 1 ? allCollapsed : null"
              :grid-size="ui.gridSize"
              :detail-pane="ui.detailPane"
              :fields="state.fields.value"
              @fields="state.setFields"
              @sort="
                (levels) => {
                  columnSort = null
                  state.setSort(levels)
                }
              "
              @layout="state.setLayout"
              @grid-size="(v) => (ui.gridSize = v)"
              @detail-pane="setDetailPane"
              @section="state.setSection"
              @toggle-all="toggleAll"
            />
            <ViewMenu
              :name="state.overview.value?.name"
              :dirty="state.dirty.value"
              @save="saveView"
              :edit-to="editTo"
              :save-as-new-to="saveAsNewTo"
              :can-delete="(state.overviews.data.value?.length ?? 0) > 1"
              @duplicate="duplicateView"
              @delete="deleting = true"
            />
          </div>
        </header>

        <div class="space-y-6 px-4 py-4 md:px-6">
          <FolderGrid
            v-if="folders.length"
            :nodes="folders"
            :platforms="platforms.data.value ?? []"
            @open="(key) => state.openPath([...state.path.value, key])"
          />

          <section>
            <h2
              v-if="folders.length"
              class="mb-2 font-mono text-[11px] tracking-wider text-muted-foreground uppercase"
            >
              {{ t('explorer.itemsHere', { n: total }) }}
            </h2>
            <div v-if="items.isPending.value" class="flex flex-wrap gap-3">
              <Skeleton
                v-for="slot in 12"
                :key="slot"
                class="aspect-[5/7] rounded-md"
                :style="{ width: `${rowHeight * 0.71}px` }"
              />
            </div>
            <Empty v-else-if="!loaded.length" class="border" data-testid="explorer-empty">
              <EmptyHeader>
                <EmptyMedia variant="icon"><SearchX /></EmptyMedia>
                <EmptyTitle>
                  {{ state.query.value ? t('explorer.noResults') : t('explorer.emptyTitle') }}
                </EmptyTitle>
                <EmptyDescription>
                  {{ state.query.value ? t('explorer.noResultsHint') : t('explorer.emptyHint') }}
                </EmptyDescription>
              </EmptyHeader>
              <EmptyContent v-if="!state.query.value && canEdit(library.data.value?.role)">
                <Button @click="ui.openAdd(state.libraryId.value, 'scan')">
                  {{ t('actions.addGame') }}
                </Button>
              </EmptyContent>
            </Empty>
            <div v-else ref="list" class="space-y-4">
              <section
                v-for="(group, g) in groups"
                :key="group.key"
                :data-testid="group.section ? 'item-section' : undefined"
                :data-section="group.section?.key"
              >
                <!-- Stuck at the top, its shadow covers the list's top padding above it. -->
                <h3
                  v-if="group.section"
                  class="sticky top-0 z-10 -mx-1 mb-2 bg-background shadow-[0_-1rem_0_var(--background)]"
                >
                  <button
                    type="button"
                    class="flex w-full min-w-0 items-center gap-2 rounded-md px-1 py-1.5 text-left hover:bg-muted/60"
                    :aria-expanded="group.open"
                    :aria-label="
                      t('explorer.toggleSection', {
                        name: label(group.section.field, group.section.key, group.section.label),
                      })
                    "
                    data-testid="section-header"
                    @click="toggleSection(group.key)"
                  >
                    <ChevronRight
                      class="size-4 shrink-0 text-muted-foreground transition-transform"
                      :class="group.open && 'rotate-90'"
                    />
                    <span class="min-w-0 truncate text-sm font-semibold">
                      {{ label(group.section.field, group.section.key, group.section.label) }}
                    </span>
                    <span class="tabular font-mono text-[11px] text-muted-foreground">
                      {{ n(group.section.count) }}
                    </span>
                    <span
                      v-if="Number(group.section.value) > 0"
                      class="tabular ml-auto shrink-0 font-mono text-[11px] text-muted-foreground"
                    >
                      {{ n(Number(group.section.value), 'currency') }}
                    </span>
                  </button>
                </h3>
                <template v-if="group.open">
                  <div
                    v-if="state.layout.value === 'grid'"
                    class="flex flex-wrap items-start gap-x-2 gap-y-3"
                    data-testid="item-grid"
                    :data-row-height="rowHeight"
                  >
                    <ItemCard
                      v-for="(item, index) in group.items"
                      :key="item.id"
                      :item="item"
                      :fields="shownFields"
                      :selected="paneOpen && item.id === state.itemId.value"
                      :width="cardWidths[g]?.[index] ?? rowHeight"
                      @open="openItem(item)"
                    />
                  </div>
                  <ItemRows
                    v-else-if="group.items.length"
                    :items="group.items"
                    :fields="shownFields"
                    :layout="state.layout.value"
                    :selected-id="paneOpen ? state.itemId.value : undefined"
                    :sort-key="tableSorted ? columnSort?.key : null"
                    :sort-desc="columnSort?.desc"
                    @sort-by="sortBy"
                    @open="(id) => openItem(loaded.find((i) => i.id === id)!)"
                  />
                </template>
              </section>
            </div>
            <div ref="sentinel" class="flex justify-center py-4">
              <Button
                v-if="wantMore"
                variant="ghost"
                size="sm"
                :disabled="items.isFetchingNextPage.value"
                data-testid="load-more"
                @click="items.fetchNextPage()"
              >
                <Spinner v-if="items.isFetchingNextPage.value" />
                {{ t('actions.loadMore') }}
              </Button>
            </div>
          </section>
        </div>
      </div>

      <footer
        class="tabular flex h-7 shrink-0 items-center gap-3 border-t bg-muted/40 px-4 font-mono text-[11px] text-muted-foreground md:px-6"
        data-testid="status-bar"
      >
        <span class="truncate">{{ statusLine }}</span>
      </footer>
    </div>

    <DetailPane
      v-if="paneOpen && state.itemId.value"
      :library-id="state.libraryId.value"
      :item-id="state.itemId.value"
      :fields="fieldsFor(state.fields.value, 'detail')"
      @close="state.selectItem(undefined)"
    />

    <DeleteViewDialog
      v-if="deleting"
      :name="state.overview.value?.name ?? ''"
      @confirm="deleteView"
      @cancel="deleting = false"
    />
  </div>
</template>
