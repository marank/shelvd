/**
 * Add-ons: optional features in src/addons/<name>/ – git-ignored here, copied in by an
 * add-on's own build together with its backend part (backend/addons/__init__.py). Each one
 * default-exports an `Addon` from its index.ts; the app plugs it in only at these seams.
 * Keep an add-on's index.ts small: pages and big components behind dynamic imports, so
 * they don't count towards the first start.
 */
import { computed, type Component, type ComputedRef } from 'vue'
import type { RouteRecordRaw } from 'vue-router'

/** A link in the sidebar (`nav`) or the user menu (`accountMenu`). */
export interface AddonLink {
  route: string
  /** i18n key of the label (add-ons bring locales/{de,en}.json like features). */
  label: string
  icon: Component
  testid: string
  /** Further route names that mark the link as current. */
  activeOn?: string[]
}

/** A figure in a game's or copy's head (`HeroStats`). */
export interface AddonFigure {
  key: string
  label: string
  value: string
  accent?: boolean
}

/** What the head shows: a game (platformId null) or one release or copy of it. */
export interface FigureTarget {
  workId: string
  platformId: string | null
}

export interface Addon {
  routes?: RouteRecordRaw[]
  nav?: AddonLink[]
  accountMenu?: AddonLink[]
  /** Called in setup of the game head and the copy hero. */
  figures?: (target: () => FigureTarget) => ComputedRef<AddonFigure[]>
  /** Shown in "Das Spiel" after HowLongToBeat; gets the release as prop `release`. */
  gameFacts?: Component[]
  /** Integration fields set by a flow of their own (not typed in): field name → section
   * shown on the integration's edit page, with the integration as prop `integration`. */
  integrationFlows?: Record<string, Component>
  /** Where an integration's service lives, by integration key. */
  integrationLinks?: Record<string, string>
  /** Ways to bring a collection in from elsewhere: links on a library's settings page (for
   * those who may edit it). The route gets `params: { libraryId }`. */
  libraryImports?: AddonLink[]
}

const modules = import.meta.glob<Addon>('./*/index.ts', { eager: true, import: 'default' })

export const addons: Addon[] = Object.values(modules)

/** Every add-on's contribution of one kind, in add-on order. */
export function collect<K extends keyof Addon>(key: K): NonNullable<Addon[K]>[] {
  return addons.flatMap((addon) => (addon[key] === undefined ? [] : [addon[key]]))
}

/** All add-ons' figures for a game, release or copy head. */
export function useAddonFigures(target: () => FigureTarget): ComputedRef<AddonFigure[]> {
  const parts = collect('figures').map((figures) => figures(target))
  return computed(() => parts.flatMap((part) => part.value))
}
