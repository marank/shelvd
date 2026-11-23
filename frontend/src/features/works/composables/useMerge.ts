import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { refDebounced } from '@vueuse/core'
import { computed, toValue, type MaybeRefOrGetter, type Ref } from 'vue'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'

/** Games by title, for choosing where a release or game should go. */
export function useWorkSearch(query: Ref<string>, exclude: MaybeRefOrGetter<string>) {
  const debounced = refDebounced(query, 250)
  return useQuery({
    queryKey: computed(() => ['works', 'search', debounced.value, toValue(exclude)]),
    queryFn: () =>
      unwrap(
        api.GET('/api/catalog/works', {
          params: { query: { q: debounced.value, exclude: toValue(exclude) || undefined } },
        }),
      ),
    enabled: computed(() => debounced.value.trim().length >= 2),
  })
}

/** Moving a release or merging a game changes games and items everywhere. */
function useInvalidateAll() {
  const client = useQueryClient()
  return () =>
    Promise.all(
      ['works', 'releases', 'items', 'tree', 'trackings'].map((key) =>
        client.invalidateQueries({ queryKey: [key] }),
      ),
    )
}

export function useMoveRelease() {
  const invalidate = useInvalidateAll()
  return useMutation({
    mutationFn: ({
      releaseId,
      workId,
      title,
    }: {
      releaseId: string
      workId?: string
      title?: string
    }) =>
      unwrap(
        api.POST('/api/catalog/releases/{release_id}/move', {
          params: { path: { release_id: releaseId } },
          body: { work_id: workId ?? null, title: title ?? '' },
        }),
      ),
    onSuccess: invalidate,
  })
}

export function useMergeWork() {
  const invalidate = useInvalidateAll()
  return useMutation({
    mutationFn: ({ workId, targetId }: { workId: string; targetId: string }) =>
      unwrap(
        api.POST('/api/catalog/works/{work_id}/merge', {
          params: { path: { work_id: workId } },
          body: { target_id: targetId },
        }),
      ),
    onSuccess: invalidate,
  })
}
