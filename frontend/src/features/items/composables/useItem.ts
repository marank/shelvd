import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { computed, toValue, watch, type MaybeRefOrGetter } from 'vue'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { ItemPatch, ReleasePatch } from '@/api/types'
import { keys } from '@/features/library/composables/queryKeys'
import { openLibrary } from '@/features/library/composables/useCurrentLibrary'

type Id = MaybeRefOrGetter<string>

export function useItem(libraryId: Id, itemId: MaybeRefOrGetter<string | undefined>) {
  return useQuery({
    queryKey: computed(() => keys.item(toValue(libraryId), toValue(itemId) ?? '')),
    queryFn: () =>
      unwrap(
        api.GET('/api/libraries/{library_id}/items/{item_id}', {
          params: { path: { library_id: toValue(libraryId), item_id: toValue(itemId) ?? '' } },
        }),
      ),
    enabled: computed(() => !!toValue(libraryId) && !!toValue(itemId)),
  })
}

/** A copy by its id alone (its page's URL has no library): finds its library, makes it
 * the current one, and then reads the copy like any other (so changes refresh it). */
export function useItemById(itemId: MaybeRefOrGetter<string>) {
  const client = useQueryClient()
  const lookup = useQuery({
    queryKey: computed(() => ['item-library', toValue(itemId)]),
    queryFn: async () => {
      const item = await unwrap(
        api.GET('/api/items/{item_id}', { params: { path: { item_id: toValue(itemId) } } }),
      )
      client.setQueryData(keys.item(item.library_id, item.id), item)
      return item.library_id
    },
    enabled: computed(() => !!toValue(itemId)),
    staleTime: Infinity,
  })
  const libraryId = computed(() => lookup.data.value ?? '')
  watch(libraryId, (id) => id && openLibrary(id), { immediate: true })
  const item = useItem(libraryId, itemId)
  const isError = computed(() => lookup.isError.value || item.isError.value)
  return { item, libraryId, isError }
}

/** Everything an item change can affect: lists, tree counts, the library's count. */
function useInvalidate(libraryId: Id) {
  const client = useQueryClient()
  return () =>
    Promise.all([
      client.invalidateQueries({ queryKey: keys.items(toValue(libraryId)) }),
      client.invalidateQueries({ queryKey: keys.tree(toValue(libraryId)) }),
      client.invalidateQueries({ queryKey: keys.loans(toValue(libraryId)) }),
      client.invalidateQueries({ queryKey: keys.people(toValue(libraryId)) }),
      client.invalidateQueries({ queryKey: keys.locations(toValue(libraryId)) }),
      client.invalidateQueries({ queryKey: keys.libraries }),
      client.invalidateQueries({ queryKey: ['works'] }),
    ])
}

/** A catalog release by id (edit page). */
export function useRelease(releaseId: MaybeRefOrGetter<string>) {
  return useQuery({
    queryKey: computed(() => ['releases', toValue(releaseId)]),
    queryFn: () =>
      unwrap(
        api.GET('/api/catalog/releases/{release_id}', {
          params: { path: { release_id: toValue(releaseId) } },
        }),
      ),
    enabled: computed(() => !!toValue(releaseId)),
  })
}

export function useItemMutations(libraryId: Id) {
  const client = useQueryClient()
  const invalidate = useInvalidate(libraryId)
  const path = (itemId: string) => ({
    params: { path: { library_id: toValue(libraryId), item_id: itemId } },
  })
  const update = useMutation({
    mutationFn: ({ id, body }: { id: string; body: ItemPatch }) =>
      unwrap(api.PATCH('/api/libraries/{library_id}/items/{item_id}', { ...path(id), body })),
    onSuccess: invalidate,
  })
  const remove = useMutation({
    mutationFn: (id: string) =>
      unwrap(api.DELETE('/api/libraries/{library_id}/items/{item_id}', path(id))),
    // Drop the deleted copy's own query first: refetching it would only answer 404.
    onSuccess: (_, id) => {
      client.removeQueries({ queryKey: keys.item(toValue(libraryId), id) })
      return invalidate()
    },
  })
  const lend = useMutation({
    mutationFn: (body: {
      item_id: string
      borrower_id: string | null
      borrower_name: string
      due_on: string | null
      notes: string
    }) =>
      unwrap(
        api.POST('/api/libraries/{library_id}/loans', {
          params: { path: { library_id: toValue(libraryId) } },
          body: { ...body, lent_on: null },
        }),
      ),
    onSuccess: invalidate,
  })
  const giveBack = useMutation({
    mutationFn: (loanId: string) =>
      unwrap(
        api.POST('/api/libraries/{library_id}/loans/{loan_id}/return', {
          params: { path: { library_id: toValue(libraryId), loan_id: loanId } },
          body: { returned_on: null },
        }),
      ),
    onSuccess: invalidate,
  })
  const uploadCover = useMutation({
    mutationFn: ({ id, file }: { id: string; file: File }) =>
      unwrap(
        api.POST('/api/libraries/{library_id}/items/{item_id}/cover', {
          ...path(id),
          body: { file } as never,
          bodySerializer: () => {
            const form = new FormData()
            form.append('file', file)
            return form
          },
        }),
      ),
    onSuccess: invalidate,
  })
  /** Everything as the release again: title, cover, edition, region, date. */
  const reset = useMutation({
    mutationFn: (id: string) =>
      unwrap(api.POST('/api/libraries/{library_id}/items/{item_id}/reset', path(id))),
    onSuccess: invalidate,
  })
  const removeCover = useMutation({
    mutationFn: (id: string) =>
      unwrap(api.DELETE('/api/libraries/{library_id}/items/{item_id}/cover', path(id))),
    onSuccess: invalidate,
  })
  /** Own cover for this copy from a covers source (a cover-candidates token). */
  const coverFrom = useMutation({
    mutationFn: ({ id, token }: { id: string; token: string }) =>
      unwrap(
        api.POST('/api/libraries/{library_id}/items/{item_id}/cover-from', {
          ...path(id),
          body: { token },
        }),
      ),
    onSuccess: invalidate,
  })
  const create = useMutation({
    mutationFn: (releaseId: string) =>
      unwrap(
        api.POST('/api/libraries/{library_id}/items', {
          params: { path: { library_id: toValue(libraryId) } },
          body: {
            release_id: releaseId,
            format: 'physical',
            status: 'owned',
            notes: '',
            title_override: '',
          },
        }),
      ),
    onSuccess: invalidate,
  })
  return { update, remove, lend, giveBack, uploadCover, removeCover, reset, coverFrom, create }
}

export function useReleaseMutations(libraryId: Id) {
  const client = useQueryClient()
  const invalidateItems = useInvalidate(libraryId)
  const invalidate = () =>
    Promise.all([
      invalidateItems(),
      client.invalidateQueries({ queryKey: ['works'] }),
      client.invalidateQueries({ queryKey: ['releases'] }),
    ])
  const path = (releaseId: string) => ({ params: { path: { release_id: releaseId } } })
  const update = useMutation({
    mutationFn: ({ id, body }: { id: string; body: ReleasePatch }) =>
      unwrap(api.PATCH('/api/catalog/releases/{release_id}', { ...path(id), body })),
    onSuccess: invalidate,
  })
  const uploadCover = useMutation({
    mutationFn: ({ id, file }: { id: string; file: File }) =>
      unwrap(
        api.POST('/api/catalog/releases/{release_id}/cover', {
          ...path(id),
          body: { file } as never,
          bodySerializer: () => {
            const form = new FormData()
            form.append('file', file)
            return form
          },
        }),
      ),
    onSuccess: invalidate,
  })
  const addBarcode = useMutation({
    mutationFn: ({ id, code }: { id: string; code: string }) =>
      unwrap(
        api.POST('/api/catalog/releases/{release_id}/barcodes', { ...path(id), body: { code } }),
      ),
    onSuccess: invalidate,
  })
  return { update, uploadCover, addBarcode }
}
