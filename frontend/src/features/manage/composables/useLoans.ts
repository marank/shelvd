import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { computed, toValue, type MaybeRefOrGetter } from 'vue'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { keys } from '@/features/library/composables/queryKeys'
import { firstText } from '@/lib/utils'

/** Open loans (open = true) or returned ones (open = false). */
export function useLoans(libraryId: MaybeRefOrGetter<string>, open: MaybeRefOrGetter<boolean>) {
  return useQuery({
    queryKey: computed(() => [...keys.loans(toValue(libraryId)), { open: toValue(open) }]),
    queryFn: () =>
      unwrap(
        api.GET('/api/libraries/{library_id}/loans', {
          params: { path: { library_id: toValue(libraryId) }, query: { open: toValue(open) } },
        }),
      ),
    enabled: computed(() => !!toValue(libraryId)),
  })
}

export function useLoanMutations(libraryId: MaybeRefOrGetter<string>) {
  const client = useQueryClient()
  const invalidate = () => {
    const id = toValue(libraryId)
    return Promise.all(
      [keys.loans(id), keys.people(id), keys.items(id), keys.tree(id), keys.libraries].map(
        (queryKey) => client.invalidateQueries({ queryKey }),
      ),
    )
  }
  const markReturned = useMutation({
    mutationFn: ({ id, returnedOn }: { id: string; returnedOn?: string | null }) =>
      unwrap(
        api.POST('/api/libraries/{library_id}/loans/{loan_id}/return', {
          params: { path: { library_id: toValue(libraryId), loan_id: id } },
          body: { returned_on: firstText(returnedOn) ?? null },
        }),
      ),
    onSuccess: invalidate,
  })
  const remove = useMutation({
    mutationFn: (id: string) =>
      unwrap(
        api.DELETE('/api/libraries/{library_id}/loans/{loan_id}', {
          params: { path: { library_id: toValue(libraryId), loan_id: id } },
        }),
      ),
    onSuccess: invalidate,
  })
  return { markReturned, remove }
}
