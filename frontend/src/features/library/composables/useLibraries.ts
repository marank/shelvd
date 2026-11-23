import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { computed, toValue, type MaybeRefOrGetter } from 'vue'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { keys } from './queryKeys'

export function useLibraries() {
  return useQuery({
    queryKey: keys.libraries,
    queryFn: () => unwrap(api.GET('/api/libraries')),
  })
}

export function useLibrary(id: MaybeRefOrGetter<string>) {
  return useQuery({
    queryKey: computed(() => keys.library(toValue(id))),
    queryFn: () =>
      unwrap(
        api.GET('/api/libraries/{library_id}', { params: { path: { library_id: toValue(id) } } }),
      ),
    enabled: computed(() => !!toValue(id)),
  })
}

export function useCreateLibrary() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: ({ name, description = '' }: { name: string; description?: string }) =>
      unwrap(api.POST('/api/libraries', { body: { name, description } })),
    onSuccess: () => client.invalidateQueries({ queryKey: keys.libraries }),
  })
}

/** Can the current user change content (items, places, loans)? */
export function canEdit(role: string | undefined): boolean {
  return role === 'owner' || role === 'editor'
}
