import { useInfiniteQuery, useQuery } from '@tanstack/vue-query'
import { computed, toValue, type MaybeRefOrGetter } from 'vue'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { keys } from '@/features/library/composables/queryKeys'
import { firstText } from '@/lib/utils'

const PAGE = 60

interface ItemsParams {
  q: string
  /** Folder levels as field:key. */
  filters: string[]
  /** The view's conditions (lib/conditions) and whether all or any must hold. */
  where: string[]
  match: 'all' | 'any'
  /** Sort levels as the API takes them: "box,-release_number". */
  sort: string
  /** A grouping field: the list comes in its groups, with their headings. */
  section?: string
}

export function useItems(
  libraryId: MaybeRefOrGetter<string>,
  params: MaybeRefOrGetter<ItemsParams>,
) {
  return useInfiniteQuery({
    queryKey: computed(() => [...keys.items(toValue(libraryId)), 'list', toValue(params)]),
    queryFn: ({ pageParam }) => {
      const p = toValue(params)
      return unwrap(
        api.GET('/api/libraries/{library_id}/items', {
          params: {
            path: { library_id: toValue(libraryId) },
            query: {
              q: p.q,
              filter: p.filters,
              where: p.where,
              match: p.match,
              sort: p.sort,
              section: firstText(p.section),
              limit: PAGE,
              offset: pageParam,
            },
          },
        }),
      )
    },
    initialPageParam: 0,
    getNextPageParam: (last, pages) => {
      const loaded = pages.reduce((n, page) => n + page.items.length, 0)
      return loaded < last.count ? loaded : undefined
    },
    enabled: computed(() => !!toValue(libraryId)),
  })
}

export function useTree(
  libraryId: MaybeRefOrGetter<string>,
  params: MaybeRefOrGetter<{
    groupBy: string[]
    q: string
    filters: string[]
    where: string[]
    match: 'all' | 'any'
  }>,
) {
  return useQuery({
    queryKey: computed(() => [...keys.tree(toValue(libraryId)), toValue(params)]),
    queryFn: () => {
      const p = toValue(params)
      return unwrap(
        api.GET('/api/libraries/{library_id}/tree', {
          params: {
            path: { library_id: toValue(libraryId) },
            query: {
              group_by: p.groupBy,
              q: p.q,
              filter: p.filters,
              where: p.where,
              match: p.match,
            },
          },
        }),
      )
    },
    enabled: computed(() => !!toValue(libraryId)),
  })
}
