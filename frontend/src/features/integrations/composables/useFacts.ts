import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { computed, toValue, watch, type MaybeRefOrGetter } from 'vue'
import { useProviders } from '@/features/library/composables/useReference'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'

/** Facts, covers and metadata change catalog data: games, releases, the items showing them
 * and the sidebar's group tree (term names). */
function useInvalidateCatalog() {
  const client = useQueryClient()
  return () =>
    Promise.all(
      [['works'], ['releases'], ['items'], ['trackings'], ['tree']].map((queryKey) =>
        client.invalidateQueries({ queryKey }),
      ),
    )
}

/** Opening a game: let the server refresh whatever facts are stale, then reload if so. */
function useRefreshFacts() {
  const invalidate = useInvalidateCatalog()
  return useMutation({
    mutationFn: ({ workId, force = false }: { workId: string; force?: boolean }) =>
      unwrap(
        api.POST('/api/catalog/works/{work_id}/facts/refresh', {
          params: { path: { work_id: workId }, query: { force } },
        }),
      ),
    onSuccess: (result) => (result.refreshed ? invalidate() : undefined),
  })
}

export function useFactCandidates(
  workId: MaybeRefOrGetter<string>,
  source: MaybeRefOrGetter<string>,
  query: MaybeRefOrGetter<string>,
) {
  return useQuery({
    queryKey: computed(() => ['facts', toValue(workId), toValue(source), toValue(query)]),
    queryFn: () =>
      unwrap(
        api.GET('/api/catalog/works/{work_id}/facts/{source}/candidates', {
          params: {
            path: { work_id: toValue(workId), source: toValue(source) },
            query: { q: toValue(query) },
          },
        }),
      ),
    retry: false,
  })
}

export function usePinFact() {
  const invalidate = useInvalidateCatalog()
  return useMutation({
    mutationFn: ({ workId, source, id }: { workId: string; source: string; id: string }) =>
      unwrap(
        api.PUT('/api/catalog/works/{work_id}/facts/{source}', {
          params: { path: { work_id: workId, source } },
          body: { external_id: id },
        }),
      ),
    onSuccess: invalidate,
  })
}

/** Forget a chosen match and search again. */
export function useUnpinFact() {
  const invalidate = useInvalidateCatalog()
  return useMutation({
    mutationFn: async ({ workId, source }: { workId: string; source: string }) => {
      await unwrap(
        api.DELETE('/api/catalog/works/{work_id}/facts/{source}', {
          params: { path: { work_id: workId, source } },
        }),
      )
      return unwrap(
        api.POST('/api/catalog/works/{work_id}/facts/refresh', {
          params: { path: { work_id: workId }, query: { force: true } },
        }),
      )
    },
    onSuccess: invalidate,
  })
}

/** Covers for a release; an empty query searches its title (and shorter forms of it). */
export function useCoverCandidates(
  releaseId: MaybeRefOrGetter<string>,
  query: MaybeRefOrGetter<string> = '',
) {
  return useQuery({
    queryKey: computed(() => ['covers', toValue(releaseId), toValue(query)]),
    queryFn: () =>
      unwrap(
        api.GET('/api/catalog/releases/{release_id}/cover-candidates', {
          params: { path: { release_id: toValue(releaseId) }, query: { q: toValue(query) } },
        }),
      ),
  })
}

export const coverPreview = (token: string) =>
  `/api/catalog/cover-preview?token=${encodeURIComponent(token)}`

export function useApplyCover() {
  const invalidate = useInvalidateCatalog()
  return useMutation({
    mutationFn: ({ releaseId, token }: { releaseId: string; token: string }) =>
      unwrap(
        api.POST('/api/catalog/releases/{release_id}/cover-from', {
          params: { path: { release_id: releaseId } },
          body: { token },
        }),
      ),
    onSuccess: invalidate,
  })
}

/** Games of a metadata source (IGDB) that may be this one; an empty query searches the title. */
export function useMetadataCandidates(
  workId: MaybeRefOrGetter<string>,
  source: MaybeRefOrGetter<string>,
  query: MaybeRefOrGetter<string>,
) {
  return useQuery({
    queryKey: computed(() => ['metadata', toValue(workId), toValue(source), toValue(query)]),
    queryFn: () =>
      unwrap(
        api.GET('/api/catalog/works/{work_id}/metadata/{source}/candidates', {
          params: {
            path: { work_id: toValue(workId), source: toValue(source) },
            query: { q: toValue(query) },
          },
        }),
      ),
    retry: false,
  })
}

/** What an entry would change in the game, field by field (current against proposed). */
export function useMetadataPreview(
  workId: MaybeRefOrGetter<string>,
  source: MaybeRefOrGetter<string>,
  externalId: MaybeRefOrGetter<string>,
) {
  return useQuery({
    queryKey: computed(() => [
      'metadata-preview',
      toValue(workId),
      toValue(source),
      toValue(externalId),
    ]),
    queryFn: () =>
      unwrap(
        api.GET('/api/catalog/works/{work_id}/metadata/{source}/{external_id}', {
          params: {
            path: {
              work_id: toValue(workId),
              source: toValue(source),
              external_id: toValue(externalId),
            },
          },
        }),
      ),
    retry: false,
  })
}

/** Link the game to the entry and apply the chosen changes (ids from the preview). */
export function useApplyMetadata() {
  const invalidate = useInvalidateCatalog()
  const client = useQueryClient()
  return useMutation({
    mutationFn: ({
      workId,
      source,
      id,
      changes,
    }: {
      workId: string
      source: string
      id: string
      changes: string[]
    }) =>
      unwrap(
        api.POST('/api/catalog/works/{work_id}/metadata/{source}', {
          params: { path: { work_id: workId, source } },
          body: { external_id: id, changes },
        }),
      ),
    onSuccess: () =>
      Promise.all([invalidate(), client.invalidateQueries({ queryKey: ['metadata-preview'] })]),
  })
}

/** Opening a game (or one of its copies) refreshes its stale facts – if a facts source is
 * switched on. Returns whether one is. */
export function useFactsOnOpen(workId: MaybeRefOrGetter<string>) {
  const providers = useProviders()
  const active = computed(() =>
    (providers.data.value ?? []).some((p) => p.kind === 'facts' && p.enabled),
  )
  const refresh = useRefreshFacts()
  watch(
    [() => toValue(workId), active],
    ([id, on]) => on && id && refresh.mutate({ workId: id }, { onError: () => {} }),
    { immediate: true },
  )
  return active
}
