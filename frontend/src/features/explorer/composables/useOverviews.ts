import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { computed, toValue, type MaybeRefOrGetter } from 'vue'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { OverviewIn } from '@/api/types'
import { keys } from '@/features/library/composables/queryKeys'
import { useUiStore } from '@/stores/ui'

export function useOverviews(libraryId: MaybeRefOrGetter<string>) {
  return useQuery({
    queryKey: computed(() => keys.overviews(toValue(libraryId))),
    queryFn: () =>
      unwrap(
        api.GET('/api/libraries/{library_id}/overviews', {
          params: { path: { library_id: toValue(libraryId) } },
        }),
      ),
    enabled: computed(() => !!toValue(libraryId)),
  })
}

export function useSaveOverview(libraryId: MaybeRefOrGetter<string>) {
  const client = useQueryClient()
  const invalidate = () =>
    client.invalidateQueries({ queryKey: keys.overviews(toValue(libraryId)) })
  const create = useMutation({
    mutationFn: (body: OverviewIn) =>
      unwrap(
        api.POST('/api/libraries/{library_id}/overviews', {
          params: { path: { library_id: toValue(libraryId) } },
          body,
        }),
      ),
    onSuccess: invalidate,
  })
  const update = useMutation({
    mutationFn: ({ id, body }: { id: string; body: Partial<OverviewIn> }) =>
      unwrap(
        api.PATCH('/api/libraries/{library_id}/overviews/{overview_id}', {
          params: { path: { library_id: toValue(libraryId), overview_id: id } },
          body,
        }),
      ),
    onSuccess: invalidate,
  })
  const remove = useMutation({
    mutationFn: (id: string) =>
      unwrap(
        api.DELETE('/api/libraries/{library_id}/overviews/{overview_id}', {
          params: { path: { library_id: toValue(libraryId), overview_id: id } },
        }),
      ),
    onSuccess: invalidate,
  })
  return { create, update, remove }
}

/** The view last opened in this library (else its first): the sidebar marks it. */
export function useLastView(libraryId: MaybeRefOrGetter<string>) {
  const ui = useUiStore()
  const overviews = useOverviews(libraryId)
  return computed(() => {
    const all = overviews.data.value ?? []
    return all.find((o) => o.id === ui.lastView[toValue(libraryId)]) ?? all[0]
  })
}
