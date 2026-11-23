import { Building2, Crown, Gamepad2, Layers, Tag, type LucideIcon } from '@lucide/vue'
import type { RouteLocationRaw } from 'vue-router'

/** Catalog terms: shared names games are tagged with, each with its own pages
 * (/companies, /genres, /franchises, /series and /<kind>/<id>). A franchise is the brand
 * ("Mario"), a series one line of games in it ("Super Mario", "Mario Kart"). */
export type TermKind = 'companies' | 'genres' | 'franchises' | 'series'
export const TERM_KINDS: TermKind[] = ['companies', 'genres', 'franchises', 'series']
/** What a source (Wikipedia, IGDB) can describe: companies, series, franchises – genres are too
 * general – and platforms (not a term, but described and pictured the same way). */
const DESCRIBED_TERMS = ['companies', 'series', 'franchises'] as const
export type DescribedKind = (typeof DESCRIBED_TERMS)[number] | 'platforms'
export const isDescribed = (kind: TermKind | 'platforms'): kind is DescribedKind =>
  kind === 'platforms' || (DESCRIBED_TERMS as readonly string[]).includes(kind)
/** Which integrations describe a kind, in the order they're offered. */
export const DESCRIPTION_SOURCES: Record<DescribedKind, string[]> = {
  companies: ['wikipedia', 'igdb'],
  series: ['wikipedia'],
  franchises: ['wikipedia'],
  platforms: ['wikipedia', 'igdb'],
}

export interface TermRef {
  id: string
  name: string
}

export const TERM_ICONS: Record<TermKind, LucideIcon> = {
  companies: Building2,
  genres: Tag,
  franchises: Crown,
  series: Layers,
}

/** Every described kind's symbol (platforms too). */
export const KIND_ICONS: Record<TermKind | 'platforms', LucideIcon> = {
  ...TERM_ICONS,
  platforms: Gamepad2,
}

/** A platform's page (/platforms/<id>). */
export const platformPage = (platformId: string): RouteLocationRaw => ({
  name: 'platforms-detail',
  params: { platformId },
})
/** The page of whatever is described: a term's or a platform's. */
export const describedPage = (kind: DescribedKind, id: string): RouteLocationRaw =>
  kind === 'platforms' ? platformPage(id) : termPage(kind, id)
const idParam = (kind: DescribedKind, id: string) =>
  kind === 'platforms' ? { platformId: id } : { termId: id }
/** Its description from a source, and choosing its picture. */
export const describeRoute = (
  kind: DescribedKind,
  id: string,
  source: string,
): RouteLocationRaw => ({
  name: `${kind}-description`,
  params: { ...idParam(kind, id), source },
})
export const imageRoute = (kind: DescribedKind, id: string): RouteLocationRaw => ({
  name: `${kind}-image`,
  params: idParam(kind, id),
})

/** Route names: the list is the kind itself, the rest `<kind>-detail|edit|merge`. */
export const termList = (kind: TermKind): RouteLocationRaw => ({ name: kind })
export const termPage = (kind: TermKind, termId: string): RouteLocationRaw => ({
  name: `${kind}-detail`,
  params: { termId },
})
