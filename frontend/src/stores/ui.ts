import { defineStore } from 'pinia'
import { ref, watch } from 'vue'

export type Theme = 'system' | 'light' | 'dark'
/** Which tab the add dialog opens on. */
export type AddMode = 'scan' | 'search'
export type AddDestination = 'library' | 'track'
const STORAGE_KEY = 'shelvd.theme'

function readTheme(): Theme {
  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (stored === 'light' || stored === 'dark' || stored === 'system') return stored
  } catch {
    // storage blocked
  }
  return 'system'
}

function prefersDark(): boolean {
  return typeof window.matchMedia === 'function'
    ? window.matchMedia('(prefers-color-scheme: dark)').matches
    : false
}

export type GridSize = 's' | 'm' | 'l'
/** How the platforms page and the overviews of companies, genres … list them. */
export type PlatformLayout = 'table' | 'tiles'
export type OverviewSort = 'name' | 'uses'

/** A per-browser preference kept in localStorage (falls back silently when blocked). */
function stored<T>(key: string, fallback: T, valid: (value: unknown) => value is T): T {
  try {
    const raw = localStorage.getItem(key)
    if (raw !== null) {
      const value: unknown = JSON.parse(raw)
      if (valid(value)) return value
    }
  } catch {
    // blocked or malformed: use the default
  }
  return fallback
}

function persist(key: string, value: unknown): void {
  try {
    localStorage.setItem(key, JSON.stringify(value))
  } catch {
    // not remembered, that's all
  }
}

const isNumber = (v: unknown): v is number => typeof v === 'number' && Number.isFinite(v)
const isBoolean = (v: unknown): v is boolean => typeof v === 'boolean'
const isGridSize = (v: unknown): v is GridSize => v === 's' || v === 'm' || v === 'l'
const isPlatformLayout = (v: unknown): v is PlatformLayout => v === 'table' || v === 'tiles'
const isOverviewSort = (v: unknown): v is OverviewSort => v === 'name' || v === 'uses'
const isStringMap = (v: unknown): v is Record<string, string> =>
  !!v &&
  typeof v === 'object' &&
  !Array.isArray(v) &&
  Object.values(v).every((x) => typeof x === 'string')

const isListMap = (v: unknown): v is Record<string, string[]> =>
  !!v &&
  typeof v === 'object' &&
  !Array.isArray(v) &&
  Object.values(v).every((x) => Array.isArray(x) && x.every((y) => typeof y === 'string'))

const isBooleanMap = (v: unknown): v is Record<string, boolean> =>
  !!v &&
  typeof v === 'object' &&
  !Array.isArray(v) &&
  Object.values(v).every((x) => typeof x === 'boolean')

export const SIDEBAR_DEFAULT = 256
export const DETAIL_DEFAULT = 480

/** Client-only UI state: theme, layout preferences and whether the add dialog is open. */
export const useUiStore = defineStore('ui', () => {
  const theme = ref<Theme>(readTheme())
  const addOpen = ref(false)
  const addLibraryId = ref<string | null>(null)
  const addMode = ref<AddMode>('search')
  /** Where the add dialog puts a game by default; null = by whether it's out yet. */
  const addDestination = ref<AddDestination | null>(null)
  const sidebarWidth = ref(stored('shelvd.sidebar-width', SIDEBAR_DEFAULT, isNumber))
  /** Show a game's details in a third column next to the explorer (desktop). */
  const detailPane = ref(stored('shelvd.detail-pane', false, isBoolean))
  const detailWidth = ref(stored('shelvd.detail-width', DETAIL_DEFAULT, isNumber))
  const gridSize = ref<GridSize>(stored('shelvd.grid-size', 'm', isGridSize))
  const platformLayout = ref<PlatformLayout>(
    stored('shelvd.platform-layout', 'table', isPlatformLayout),
  )
  watch(platformLayout, (v) => persist('shelvd.platform-layout', v))
  const termLayout = ref<PlatformLayout>(stored('shelvd.term-layout', 'table', isPlatformLayout))
  watch(termLayout, (v) => persist('shelvd.term-layout', v))
  const termSort = ref<OverviewSort>(stored('shelvd.term-sort', 'name', isOverviewSort))
  watch(termSort, (v) => persist('shelvd.term-sort', v))
  /** Phone scanning: add a barcode we already know without asking. */
  const scanAutoAdd = ref(stored('shelvd.scan-auto-add', true, isBoolean))
  /** The view last opened in each library (library id → view id): game, release and
   * copy pages show its detail fields, the sidebar marks it. */
  const lastView = ref(stored('shelvd.last-view', {}, isStringMap))
  watch(lastView, (v) => persist('shelvd.last-view', v), { deep: true })
  /** Folded-in section headings of the item list ("library|field" → group keys). */
  const collapsed = ref(stored('shelvd.collapsed-sections', {}, isListMap))
  watch(collapsed, (v) => persist('shelvd.collapsed-sections', v), { deep: true })
  /** Sections of the game page opened or closed by hand ("<focus>.<section>" → open);
   * the others follow the page's defaults. */
  const gameSections = ref(stored('shelvd.game-sections', {}, isBooleanMap))
  watch(gameSections, (v) => persist('shelvd.game-sections', v), { deep: true })
  watch(sidebarWidth, (v) => persist('shelvd.sidebar-width', v))
  watch(detailPane, (v) => persist('shelvd.detail-pane', v))
  watch(detailWidth, (v) => persist('shelvd.detail-width', v))
  watch(gridSize, (v) => persist('shelvd.grid-size', v))
  watch(scanAutoAdd, (v) => persist('shelvd.scan-auto-add', v))

  function apply(): void {
    const dark = theme.value === 'dark' || (theme.value === 'system' && prefersDark())
    document.documentElement.classList.toggle('dark', dark)
  }

  function setTheme(value: Theme): void {
    theme.value = value
  }

  function openAdd(
    libraryId: string,
    mode: AddMode = 'search',
    destination: AddDestination | null = null,
  ): void {
    addLibraryId.value = libraryId
    addMode.value = mode
    addDestination.value = destination
    addOpen.value = true
  }

  watch(theme, (value) => {
    try {
      localStorage.setItem(STORAGE_KEY, value)
    } catch {
      // storage blocked: the theme is just not remembered
    }
    apply()
  })

  return {
    theme,
    addOpen,
    addLibraryId,
    addMode,
    addDestination,
    sidebarWidth,
    detailPane,
    detailWidth,
    gridSize,
    platformLayout,
    termLayout,
    termSort,
    scanAutoAdd,
    lastView,
    collapsed,
    gameSections,
    setTheme,
    openAdd,
    apply,
  }
})
