import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { computed, toValue, type MaybeRefOrGetter } from 'vue'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { ItemIn, ReleaseIn } from '@/api/types'
import type { components } from '@/api/schema'
import { CHOICES } from '@/features/items/components/options'
import { keys } from '@/features/library/composables/queryKeys'

export type ImportIn = components['schemas']['ImportIn']
export type Region = components['schemas']['Region']

export const REGIONS: Region[] = CHOICES.region

export function isRegion(value: unknown): value is Region {
  return typeof value === 'string' && (REGIONS as string[]).includes(value)
}

interface SearchParams {
  q: string
  platform: string
}

/** Minimum query length before searching. */
const MIN_QUERY = 2

/** Remember a scanned code for a release that is already in the catalog. */
export function attachBarcode(releaseId: string, code: string) {
  return unwrap(
    api.POST('/api/catalog/releases/{release_id}/barcodes', {
      params: { path: { release_id: releaseId } },
      body: { code },
    }),
  )
}

/** A barcode or article number rather than a title: "0045496420055", "NTR-IPKD-NOE". */
export function looksLikeCode(text: string): boolean {
  return /^(?=.*[\d-])[0-9A-Z./-]{7,32}$/.test(text.replace(/\s+/g, ''))
}

export function lookupBarcode(code: string) {
  return unwrap(api.GET('/api/lookup/barcode/{code}', { params: { path: { code } } }))
}

/** Releases already in our catalog. */
export function useCatalogSearch(params: MaybeRefOrGetter<SearchParams>) {
  return useQuery({
    queryKey: computed(() => ['add', 'catalog', toValue(params)]),
    queryFn: () => {
      const { q, platform } = toValue(params)
      return unwrap(
        api.GET('/api/catalog/releases', {
          params: { query: { q: q.trim(), platform: platform || null } },
        }),
      )
    },
    enabled: computed(() => toValue(params).q.trim().length >= MIN_QUERY),
  })
}

/** Candidates from online sources (IGDB). */
export function useProviderSearch(
  params: MaybeRefOrGetter<SearchParams>,
  allowed: MaybeRefOrGetter<boolean>,
) {
  return useQuery({
    queryKey: computed(() => ['add', 'provider', toValue(params)]),
    queryFn: () => {
      const { q, platform } = toValue(params)
      return unwrap(
        api.GET('/api/lookup/search', {
          params: { query: { q: q.trim(), platform: platform || null } },
        }),
      )
    },
    enabled: computed(() => toValue(allowed) && toValue(params).q.trim().length >= MIN_QUERY),
    staleTime: 5 * 60 * 1000,
  })
}

export function useImportCandidate() {
  return useMutation({
    mutationFn: (body: ImportIn) => unwrap(api.POST('/api/lookup/import', { body })),
  })
}

export function useCreateRelease() {
  return useMutation({
    mutationFn: (body: ReleaseIn) => unwrap(api.POST('/api/catalog/releases', { body })),
  })
}

export function useCreateItem(libraryId: MaybeRefOrGetter<string>) {
  const client = useQueryClient()
  return useMutation({
    mutationFn: (body: ItemIn) =>
      unwrap(
        api.POST('/api/libraries/{library_id}/items', {
          params: { path: { library_id: toValue(libraryId) } },
          body,
        }),
      ),
    onSuccess: () => {
      const id = toValue(libraryId)
      return Promise.all([
        client.invalidateQueries({ queryKey: keys.items(id) }),
        client.invalidateQueries({ queryKey: keys.tree(id) }),
        client.invalidateQueries({ queryKey: keys.libraries }),
      ])
    },
  })
}
