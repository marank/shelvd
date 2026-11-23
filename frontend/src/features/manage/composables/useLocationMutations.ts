import { useMutation, useQueryClient } from '@tanstack/vue-query'
import { toValue, type MaybeRefOrGetter } from 'vue'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/schema'
import { keys } from '@/features/library/composables/queryKeys'

export type LocationIn = components['schemas']['LocationIn']
export type LocationPatch = components['schemas']['LocationPatch']

export function useLocationMutations(libraryId: MaybeRefOrGetter<string>) {
  const client = useQueryClient()
  const invalidate = () => {
    const id = toValue(libraryId)
    return Promise.all(
      [keys.locations(id), keys.items(id), keys.tree(id)].map((queryKey) =>
        client.invalidateQueries({ queryKey }),
      ),
    )
  }
  const create = useMutation({
    mutationFn: (body: LocationIn) =>
      unwrap(
        api.POST('/api/libraries/{library_id}/locations', {
          params: { path: { library_id: toValue(libraryId) } },
          body,
        }),
      ),
    onSuccess: invalidate,
  })
  const update = useMutation({
    mutationFn: ({ id, body }: { id: string; body: LocationPatch }) =>
      unwrap(
        api.PATCH('/api/libraries/{library_id}/locations/{location_id}', {
          params: { path: { library_id: toValue(libraryId), location_id: id } },
          body,
        }),
      ),
    onSuccess: invalidate,
  })
  const remove = useMutation({
    mutationFn: (id: string) =>
      unwrap(
        api.DELETE('/api/libraries/{library_id}/locations/{location_id}', {
          params: { path: { library_id: toValue(libraryId), location_id: id } },
        }),
      ),
    onSuccess: invalidate,
  })
  return { create, update, remove }
}
