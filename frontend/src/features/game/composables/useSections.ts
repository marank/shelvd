import { toValue, type MaybeRefOrGetter } from 'vue'
import { useUiStore } from '@/stores/ui'
import type { Focus } from './useGamePage'

/** The game page's sections, always in this order: yours first, then the release, the
 * game, all its releases, more of its series and where to go from here. */
export type Section = 'copy' | 'collection' | 'release' | 'game' | 'releases' | 'series' | 'links'

/** Closed until opened: on a copy's page all releases are one click away (the copy is in
 * front); everything else is open. */
const CLOSED: Record<Focus, Section[]> = {
  item: ['releases'],
  release: [],
  work: [],
}

/** Whether a section is open – by hand (remembered per focus in this browser) or by the
 * page's default – and toggling it. */
export function useSections(focus: MaybeRefOrGetter<Focus>) {
  const ui = useUiStore()
  const key = (section: Section) => `${toValue(focus)}.${section}`
  const isOpen = (section: Section) =>
    ui.gameSections[key(section)] ?? !CLOSED[toValue(focus)].includes(section)
  const setOpen = (section: Section, open: boolean) => {
    ui.gameSections = { ...ui.gameSections, [key(section)]: open }
  }
  return { isOpen, setOpen }
}
