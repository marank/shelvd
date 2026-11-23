import { useInfiniteQuery, useQuery } from '@tanstack/vue-query'
import { computed, toValue, type MaybeRefOrGetter } from 'vue'
import { api } from '@/api/client'
import { ApiError, unwrap } from '@/api/errors'
import { DEFAULT_SORT } from '@/lib/itemFields'

const PAGE = 60

/** Did a query fail because the share link is unknown or revoked? */
export function isGone(error: unknown): boolean {
  return error instanceof ApiError && error.status === 404
}

const publicKey = (token: string) => ['public', token] as const

export function usePublicLibrary(token: MaybeRefOrGetter<string>) {
  return useQuery({
    queryKey: computed(() => [...publicKey(toValue(token)), 'library']),
    queryFn: () =>
      unwrap(
        api.GET('/api/public/libraries/{token}', { params: { path: { token: toValue(token) } } }),
      ),
  })
}

export function usePublicTree(token: MaybeRefOrGetter<string>, groupBy: MaybeRefOrGetter<string>) {
  return useQuery({
    queryKey: computed(() => [...publicKey(toValue(token)), 'tree', toValue(groupBy)]),
    queryFn: () =>
      unwrap(
        api.GET('/api/public/libraries/{token}/tree', {
          params: { path: { token: toValue(token) }, query: { group_by: [toValue(groupBy)] } },
        }),
      ),
  })
}

export function usePublicItems(
  token: MaybeRefOrGetter<string>,
  filters: MaybeRefOrGetter<string[]>,
) {
  return useInfiniteQuery({
    queryKey: computed(() => [...publicKey(toValue(token)), 'items', toValue(filters)]),
    queryFn: ({ pageParam }) =>
      unwrap(
        api.GET('/api/public/libraries/{token}/items', {
          params: {
            path: { token: toValue(token) },
            query: { filter: toValue(filters), sort: DEFAULT_SORT, limit: PAGE, offset: pageParam },
          },
        }),
      ),
    initialPageParam: 0,
    getNextPageParam: (last, pages) => {
      const loaded = pages.reduce((n, page) => n + page.items.length, 0)
      return loaded < last.count ? loaded : undefined
    },
  })
}

export function usePublicList(token: MaybeRefOrGetter<string>) {
  return useQuery({
    queryKey: computed(() => [...publicKey(toValue(token)), 'list']),
    queryFn: () =>
      unwrap(api.GET('/api/public/lists/{token}', { params: { path: { token: toValue(token) } } })),
  })
}
