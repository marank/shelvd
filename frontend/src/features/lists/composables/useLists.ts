import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { computed, toValue, type MaybeRefOrGetter } from 'vue'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { ListEntry } from '@/api/types'
import { keys } from '@/features/library/composables/queryKeys'

const entriesKey = (listId: string) => [...keys.list(listId), 'entries'] as const

/** URL of a list's public page. */
export function publicListUrl(token: string): string {
  return `${window.location.origin}/share/list/${token}`
}

export function useLists() {
  return useQuery({
    queryKey: keys.lists,
    queryFn: () => unwrap(api.GET('/api/lists')),
  })
}

export function useList(listId: MaybeRefOrGetter<string>) {
  return useQuery({
    queryKey: computed(() => keys.list(toValue(listId))),
    queryFn: () =>
      unwrap(api.GET('/api/lists/{list_id}', { params: { path: { list_id: toValue(listId) } } })),
    enabled: computed(() => !!toValue(listId)),
  })
}

export function useEntries(listId: MaybeRefOrGetter<string>) {
  return useQuery({
    queryKey: computed(() => entriesKey(toValue(listId))),
    queryFn: () =>
      unwrap(
        api.GET('/api/lists/{list_id}/entries', {
          params: { path: { list_id: toValue(listId) } },
        }),
      ),
    select: (entries: ListEntry[]) => [...entries].sort((a, b) => a.position - b.position),
  })
}

/** Every list mutation refreshes all list queries (they share the "lists" prefix). */
function useInvalidate() {
  const client = useQueryClient()
  return () => client.invalidateQueries({ queryKey: keys.lists })
}

export function useCreateList() {
  const onSuccess = useInvalidate()
  return useMutation({
    mutationFn: (body: { name: string; description: string }) =>
      unwrap(api.POST('/api/lists', { body })),
    onSuccess,
  })
}

export function useUpdateList(listId: MaybeRefOrGetter<string>) {
  const onSuccess = useInvalidate()
  return useMutation({
    mutationFn: (body: { name: string; description: string }) =>
      unwrap(
        api.PATCH('/api/lists/{list_id}', {
          params: { path: { list_id: toValue(listId) } },
          body,
        }),
      ),
    onSuccess,
  })
}

export function useDeleteList(listId: MaybeRefOrGetter<string>) {
  const client = useQueryClient()
  return useMutation({
    mutationFn: () =>
      unwrap(
        api.DELETE('/api/lists/{list_id}', { params: { path: { list_id: toValue(listId) } } }),
      ),
    onSuccess: () => {
      client.removeQueries({ queryKey: keys.list(toValue(listId)) })
      return client.invalidateQueries({ queryKey: keys.lists })
    },
  })
}

export function usePublicLink(listId: MaybeRefOrGetter<string>) {
  const onSuccess = useInvalidate()
  return useMutation({
    mutationFn: (enabled: boolean) => {
      const options = { params: { path: { list_id: toValue(listId) } } }
      return unwrap(
        enabled
          ? api.POST('/api/lists/{list_id}/public-link', options)
          : api.DELETE('/api/lists/{list_id}/public-link', options),
      )
    },
    onSuccess,
  })
}

export function useAddEntry() {
  const onSuccess = useInvalidate()
  return useMutation({
    mutationFn: ({
      listId,
      releaseId,
      itemId,
    }: {
      listId: string
      releaseId: string
      itemId?: string
    }) =>
      unwrap(
        api.POST('/api/lists/{list_id}/entries', {
          params: { path: { list_id: listId } },
          body: { release_id: releaseId, item_id: itemId ?? null, note: '' },
        }),
      ),
    onSuccess,
  })
}

export function useUpdateEntry(listId: MaybeRefOrGetter<string>) {
  const onSuccess = useInvalidate()
  return useMutation({
    mutationFn: ({ entryId, ...body }: { entryId: string; note?: string; position?: number }) =>
      unwrap(
        api.PATCH('/api/lists/{list_id}/entries/{entry_id}', {
          params: { path: { list_id: toValue(listId), entry_id: entryId } },
          body,
        }),
      ),
    onSuccess,
  })
}

/** Move an entry one step up or down: every entry whose position changes gets a PATCH. */
export function useMoveEntry(listId: MaybeRefOrGetter<string>) {
  const onSuccess = useInvalidate()
  return useMutation({
    mutationFn: async ({
      entries,
      index,
      delta,
    }: {
      entries: ListEntry[]
      index: number
      delta: -1 | 1
    }) => {
      const order = [...entries]
      const target = index + delta
      ;[order[index], order[target]] = [order[target]!, order[index]!]
      // Swap the two positions when they differ, else renumber (positions may collide).
      const a = entries[index]!
      const b = entries[target]!
      const changes =
        a.position !== b.position
          ? [
              { id: a.id, position: b.position },
              { id: b.id, position: a.position },
            ]
          : order
              .map((e, i) => ({ id: e.id, position: i + 1, old: e.position }))
              .filter((c) => c.position !== c.old)
      for (const change of changes) {
        await unwrap(
          api.PATCH('/api/lists/{list_id}/entries/{entry_id}', {
            params: { path: { list_id: toValue(listId), entry_id: change.id } },
            body: { position: change.position },
          }),
        )
      }
    },
    onSettled: onSuccess,
  })
}

export function useRemoveEntry(listId: MaybeRefOrGetter<string>) {
  const onSuccess = useInvalidate()
  return useMutation({
    mutationFn: (entryId: string) =>
      unwrap(
        api.DELETE('/api/lists/{list_id}/entries/{entry_id}', {
          params: { path: { list_id: toValue(listId), entry_id: entryId } },
        }),
      ),
    onSuccess,
  })
}
