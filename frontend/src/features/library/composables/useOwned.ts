import { useQuery } from '@tanstack/vue-query'
import { computed, toValue, type MaybeRefOrGetter } from 'vue'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { keys } from './queryKeys'

/** Owned (not sold) copies in the library, per release and per game. Lives under the
 * library's item key, so adding or removing a copy refreshes it. */
export interface Owned {
  releases: Map<string, number>
  works: Map<string, number>
}

export function useOwned(libraryId: MaybeRefOrGetter<string>) {
  return useQuery({
    queryKey: computed(() => [...keys.items(toValue(libraryId)), 'owned']),
    queryFn: () =>
      unwrap(
        api.GET('/api/libraries/{library_id}/owned', {
          params: { path: { library_id: toValue(libraryId) } },
        }),
      ),
    select: (rows): Owned => {
      const releases = new Map<string, number>()
      const works = new Map<string, number>()
      for (const row of rows) {
        releases.set(row.release_id, row.copies)
        works.set(row.work_id, (works.get(row.work_id) ?? 0) + row.copies)
      }
      return { releases, works }
    },
    enabled: computed(() => !!toValue(libraryId)),
  })
}
