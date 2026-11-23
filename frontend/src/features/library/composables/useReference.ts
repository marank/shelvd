import { useQuery } from '@tanstack/vue-query'
import { computed, toValue, type MaybeRefOrGetter } from 'vue'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { keys } from './queryKeys'

export function usePlatforms() {
  return useQuery({
    queryKey: keys.platforms,
    queryFn: () => unwrap(api.GET('/api/catalog/platforms')),
    staleTime: 60 * 60 * 1000,
  })
}

export function useLocations(libraryId: MaybeRefOrGetter<string>) {
  return useQuery({
    queryKey: computed(() => keys.locations(toValue(libraryId))),
    queryFn: () =>
      unwrap(
        api.GET('/api/libraries/{library_id}/locations', {
          params: { path: { library_id: toValue(libraryId) } },
        }),
      ),
    enabled: computed(() => !!toValue(libraryId)),
  })
}

export function usePeople(libraryId: MaybeRefOrGetter<string>) {
  return useQuery({
    queryKey: computed(() => keys.people(toValue(libraryId))),
    queryFn: () =>
      unwrap(
        api.GET('/api/libraries/{library_id}/people', {
          params: { path: { library_id: toValue(libraryId) } },
        }),
      ),
    enabled: computed(() => !!toValue(libraryId)),
  })
}

export function useProviders() {
  return useQuery({
    queryKey: keys.providers,
    queryFn: () => unwrap(api.GET('/api/lookup/providers')),
    staleTime: 5 * 60 * 1000,
  })
}
