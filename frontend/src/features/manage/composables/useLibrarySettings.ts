import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { computed, toValue, type MaybeRefOrGetter } from 'vue'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/schema'
import { keys } from '@/features/library/composables/queryKeys'

export type MemberRole = components['schemas']['Role']

export function useMembers(libraryId: MaybeRefOrGetter<string>) {
  return useQuery({
    queryKey: computed(() => keys.members(toValue(libraryId))),
    queryFn: () =>
      unwrap(
        api.GET('/api/libraries/{library_id}/members', {
          params: { path: { library_id: toValue(libraryId) } },
        }),
      ),
    enabled: computed(() => !!toValue(libraryId)),
  })
}

export function useMemberMutations(libraryId: MaybeRefOrGetter<string>) {
  const client = useQueryClient()
  const invalidate = () => client.invalidateQueries({ queryKey: keys.members(toValue(libraryId)) })
  const add = useMutation({
    mutationFn: (body: { username: string; role: MemberRole }) =>
      unwrap(
        api.POST('/api/libraries/{library_id}/members', {
          params: { path: { library_id: toValue(libraryId) } },
          body,
        }),
      ),
    onSuccess: invalidate,
  })
  const setRole = useMutation({
    mutationFn: ({ id, role }: { id: string; role: MemberRole }) =>
      unwrap(
        api.PATCH('/api/libraries/{library_id}/members/{member_id}', {
          params: { path: { library_id: toValue(libraryId), member_id: id } },
          body: { role },
        }),
      ),
    onSuccess: invalidate,
  })
  const remove = useMutation({
    mutationFn: (id: string) =>
      unwrap(
        api.DELETE('/api/libraries/{library_id}/members/{member_id}', {
          params: { path: { library_id: toValue(libraryId), member_id: id } },
        }),
      ),
    onSuccess: invalidate,
  })
  return { add, setRole, remove }
}

export function useLibraryMutations(libraryId: MaybeRefOrGetter<string>) {
  const client = useQueryClient()
  const invalidate = () =>
    Promise.all([
      client.invalidateQueries({ queryKey: keys.library(toValue(libraryId)) }),
      client.invalidateQueries({ queryKey: keys.libraries }),
    ])
  const path = () => ({ params: { path: { library_id: toValue(libraryId) } } })
  const update = useMutation({
    mutationFn: (body: components['schemas']['LibraryPatch']) =>
      unwrap(api.PATCH('/api/libraries/{library_id}', { ...path(), body })),
    onSuccess: invalidate,
  })
  const enableLink = useMutation({
    mutationFn: () => unwrap(api.POST('/api/libraries/{library_id}/public-link', path())),
    onSuccess: invalidate,
  })
  const disableLink = useMutation({
    mutationFn: () => unwrap(api.DELETE('/api/libraries/{library_id}/public-link', path())),
    onSuccess: invalidate,
  })
  const remove = useMutation({
    mutationFn: () => unwrap(api.DELETE('/api/libraries/{library_id}', path())),
    // The library is gone: drop its cached detail instead of refetching it.
    onSuccess: () => {
      client.removeQueries({ queryKey: keys.library(toValue(libraryId)), exact: true })
      return client.invalidateQueries({ queryKey: keys.libraries })
    },
  })
  return { update, enableLink, disableLink, remove }
}
