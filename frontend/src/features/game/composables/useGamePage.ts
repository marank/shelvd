import { computed } from 'vue'
import { useRoute } from 'vue-router'
import type { Item, Release } from '@/api/types'
import { useItemById, useRelease } from '@/features/items/composables/useItem'
import { useCurrentLibrary } from '@/features/library/composables/useCurrentLibrary'
import { useWork, useWorkItems } from '@/features/works/composables/useWork'
import { firstText } from '@/lib/utils'

/** What the game page is focused on: a copy (/items/<id>), a release (/releases/<id>) or
 * the game itself (/works/<id>). It's one page – the game with its releases and your
 * copies –, the focus decides what's in front. */
export type Focus = 'item' | 'release' | 'work'

/** Everything the game page shows, loaded by the route's focus. A copy's page uses the
 * copy's library (and makes it the current one), the others the current library. */
export function useGamePage() {
  const route = useRoute()
  const focus = computed<Focus>(() =>
    route.name === 'item' ? 'item' : route.name === 'release' ? 'release' : 'work',
  )
  const param = (name: string, on: Focus) =>
    computed(() => (focus.value === on ? String(route.params[name] ?? '') : ''))
  const itemId = param('itemId', 'item')
  const releaseId = param('releaseId', 'release')
  const ownWorkId = param('workId', 'work')

  const byItem = useItemById(itemId)
  const byRelease = useRelease(releaseId)
  const current = useCurrentLibrary()
  const libraryId = computed(() =>
    focus.value === 'item' ? byItem.libraryId.value : current.id.value,
  )
  const item = computed<Item | undefined>(() =>
    focus.value === 'item' ? byItem.item.data.value : undefined,
  )
  const workId = computed(
    () =>
      firstText(ownWorkId.value, byRelease.data.value?.work_id, item.value?.release.work_id) ?? '',
  )
  const work = useWork(workId)
  const items = useWorkItems(libraryId, workId)
  const copies = computed<Item[]>(() => items.data.value?.items ?? [])
  const releases = computed<Release[]>(() => work.data.value?.releases ?? [])

  /** The release the page is about – its game fields are the game's: the copy's (with the
   * copy's own values), the opened one, or for the game the next upcoming, else the first. */
  const release = computed<Release | undefined>(() => {
    if (focus.value === 'item') return item.value?.release
    if (focus.value === 'release') return byRelease.data.value
    return releases.value.find((r) => !r.is_released) ?? releases.value[0]
  })

  const loaded = computed(() => !!release.value && (focus.value !== 'work' || !!work.data.value))
  const isError = computed(
    () =>
      (focus.value === 'item' && byItem.isError.value) ||
      (focus.value === 'release' && byRelease.isError.value) ||
      (focus.value === 'work' && (work.isError.value || (!!work.data.value && !release.value))),
  )
  return {
    focus,
    libraryId,
    item,
    release,
    work,
    workId,
    releases,
    copies,
    copiesPending: computed(() => items.isPending.value),
    loaded,
    isError,
  }
}
