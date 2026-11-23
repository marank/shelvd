import { useQuery } from '@tanstack/vue-query'
import { refDebounced } from '@vueuse/core'
import { computed, ref, toValue, type MaybeRefOrGetter, type Ref } from 'vue'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { TermKind } from '@/lib/terms'

export type { TermKind }
/** Catalog terms you pick (entities with ids) and the edition label (free text). */
export type SuggestionKind = TermKind | 'editions'
/** A picked term: an existing one has its id; a new one only its name (created on save). */
export interface PickedTerm {
  id?: string
  name: string
}
export interface Suggestion {
  id?: string
  name: string
  uses: number
}

const LIMIT = 8

function fetchSuggestions(kind: SuggestionKind, q: string): Promise<Suggestion[]> {
  const params = { params: { query: { q, limit: LIMIT } } }
  switch (kind) {
    case 'companies':
      return unwrap(api.GET('/api/catalog/companies', params))
    case 'genres':
      return unwrap(api.GET('/api/catalog/genres', params))
    case 'series':
      return unwrap(api.GET('/api/catalog/series', params))
    case 'franchises':
      return unwrap(api.GET('/api/catalog/franchises', params))
    case 'editions':
      return unwrap(api.GET('/api/catalog/editions', params))
  }
}

/** Suggestions for what's typed (debounced), only while the list is open. */
export function useSuggestions(
  kind: MaybeRefOrGetter<SuggestionKind>,
  query: Ref<string>,
  open: Ref<boolean>,
) {
  const typed = refDebounced(query, 200)
  return useQuery({
    queryKey: computed(() => ['suggestions', toValue(kind), typed.value.trim()]),
    queryFn: () => fetchSuggestions(toValue(kind), typed.value.trim()),
    enabled: open,
    staleTime: 30_000,
    placeholderData: (previous) => previous,
  })
}

/** Keyboard and active option of a suggestion list: ↑ ↓ move, Enter picks, Esc closes. */
export function useListbox<T>(options: Ref<T[]>, pick: (option: T) => void) {
  const open = ref(false)
  const active = ref(0)
  function onKeydown(event: KeyboardEvent) {
    const count = options.value.length
    if (event.key === 'ArrowDown') {
      event.preventDefault()
      if (!open.value) open.value = true
      else if (count) active.value = (active.value + 1) % count
    } else if (event.key === 'ArrowUp') {
      event.preventDefault()
      if (count) active.value = (active.value - 1 + count) % count
    } else if (event.key === 'Enter') {
      const option = options.value[active.value]
      if (open.value && option !== undefined) {
        event.preventDefault() // not the form's submit
        pick(option)
      }
    } else if (event.key === 'Escape' && open.value) {
      event.preventDefault()
      event.stopPropagation()
      open.value = false
    }
  }
  return { open, active, onKeydown }
}

/** Picked terms as the API wants them: existing ones by id, new ones by name. */
export const termRefs = (terms: PickedTerm[]) =>
  terms.map((term) => (term.id ? { id: term.id } : { name: term.name }))
