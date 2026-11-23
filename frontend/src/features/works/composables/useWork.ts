import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { computed, toValue, type MaybeRefOrGetter } from 'vue'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { WorkPatch } from '@/api/types'
import { keys } from '@/features/library/composables/queryKeys'

export function useWork(workId: MaybeRefOrGetter<string>) {
  return useQuery({
    queryKey: computed(() => keys.work(toValue(workId))),
    queryFn: () =>
      unwrap(
        api.GET('/api/catalog/works/{work_id}', { params: { path: { work_id: toValue(workId) } } }),
      ),
    enabled: computed(() => !!toValue(workId)),
  })
}

export function useUpdateWork(workId: MaybeRefOrGetter<string>) {
  const client = useQueryClient()
  return useMutation({
    mutationFn: (body: WorkPatch) =>
      unwrap(
        api.PATCH('/api/catalog/works/{work_id}', {
          params: { path: { work_id: toValue(workId) } },
          body,
        }),
      ),
    onSuccess: () =>
      Promise.all([
        client.invalidateQueries({ queryKey: keys.work(toValue(workId)) }),
        client.invalidateQueries({ queryKey: ['items'] }),
        client.invalidateQueries({ queryKey: ['releases'] }),
      ]),
  })
}

/** The game's own general cover (key art): upload replaces it, remove drops it. */
export function useWorkCover(workId: MaybeRefOrGetter<string>) {
  const client = useQueryClient()
  const path = () => ({ params: { path: { work_id: toValue(workId) } } })
  const refresh = () =>
    Promise.all([
      client.invalidateQueries({ queryKey: keys.work(toValue(workId)) }),
      client.invalidateQueries({ queryKey: ['items'] }),
      client.invalidateQueries({ queryKey: ['releases'] }),
      client.invalidateQueries({ queryKey: ['terms'] }),
    ])
  const upload = useMutation({
    mutationFn: (file: File) =>
      unwrap(
        api.POST('/api/catalog/works/{work_id}/cover', {
          ...path(),
          body: { file } as never,
          bodySerializer: () => {
            const form = new FormData()
            form.append('file', file)
            return form
          },
        }),
      ),
    onSuccess: refresh,
  })
  const remove = useMutation({
    mutationFn: () => unwrap(api.DELETE('/api/catalog/works/{work_id}/cover', path())),
    onSuccess: refresh,
  })
  return { upload, remove }
}

/** The copies of one game in a library. */
export function useWorkItems(
  libraryId: MaybeRefOrGetter<string>,
  workId: MaybeRefOrGetter<string>,
) {
  return useQuery({
    queryKey: computed(() => [...keys.items(toValue(libraryId)), 'work', toValue(workId)]),
    queryFn: () =>
      unwrap(
        api.GET('/api/libraries/{library_id}/items', {
          params: {
            path: { library_id: toValue(libraryId) },
            query: { work: toValue(workId), limit: 500 },
          },
        }),
      ),
    enabled: computed(() => !!toValue(libraryId) && !!toValue(workId)),
  })
}

/** Tracking entries (own and shared) for this game. */
export function useWorkTrackings(workId: MaybeRefOrGetter<string>) {
  return useQuery({
    queryKey: computed(() => [...keys.trackings, 'work', toValue(workId)]),
    queryFn: () =>
      unwrap(api.GET('/api/watchlist', { params: { query: { work: toValue(workId) } } })),
    enabled: computed(() => !!toValue(workId)),
  })
}
