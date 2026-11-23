import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { computed, toValue, type MaybeRefOrGetter } from 'vue'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/schema'
import { keys } from '@/features/library/composables/queryKeys'
import { useProviders } from '@/features/library/composables/useReference'
import { usePlatform } from '@/features/platforms/composables/usePlatforms'
import { DESCRIPTION_SOURCES, isDescribed, type DescribedKind, type TermKind } from '@/lib/terms'

type TermDetail = components['schemas']['TermDetailOut']
export type TermListEntry = components['schemas']['TermSuggestionOut']
export type TermWork = components['schemas']['TermWorkOut']
export type CompanyDetailsIn = components['schemas']['CompanyDetailsIn']

/** All of a kind (the overview page), with how often each is used. */
export function useTermList(kind: MaybeRefOrGetter<TermKind>) {
  return useQuery({
    queryKey: computed(() => ['terms', toValue(kind)]),
    queryFn: () =>
      unwrap(
        api.GET(`/api/catalog/${toValue(kind)}`, { params: { query: { limit: 1000 } } }),
      ) as Promise<TermListEntry[]>,
  })
}

/** One term with its games (a company: developed and published ones). */
export function useTerm(kind: MaybeRefOrGetter<TermKind>, termId: MaybeRefOrGetter<string>) {
  return useQuery({
    queryKey: computed(() => ['terms', toValue(kind), toValue(termId)]),
    queryFn: () =>
      unwrap(
        api.GET(`/api/catalog/${toValue(kind)}/{term_id}`, {
          params: { path: { term_id: toValue(termId) } },
        }),
      ) as Promise<TermDetail>,
    enabled: computed(() => !!toValue(termId)),
  })
}

/** Every game of a term once (a company may have developed and published the same). */
export function termGames(data: TermDetail | undefined): TermWork[] {
  if (!data) return []
  return [...new Map([...data.works, ...data.published].map((w) => [w.id, w])).values()]
}

/** Terms show on games, releases, copies and trackings: reload them after a change. */
export function useTermMutations(kind: MaybeRefOrGetter<TermKind>) {
  const client = useQueryClient()
  const invalidate = () =>
    Promise.all(
      ['terms', 'suggestions', 'works', 'releases', 'items', 'trackings', 'tree'].map((key) =>
        client.invalidateQueries({ queryKey: [key] }),
      ),
    )
  const path = (termId: string) => ({ params: { path: { term_id: termId } } })
  return {
    update: useMutation({
      mutationFn: ({
        termId,
        ...body
      }: {
        termId: string
        name?: string
        descriptions?: Record<string, string>
        company?: CompanyDetailsIn
        series?: { franchise: { id: string } | null }
      }) => unwrap(api.PATCH(`/api/catalog/${toValue(kind)}/{term_id}`, { ...path(termId), body })),
      onSuccess: invalidate,
    }),
    uploadImage: useMutation({
      mutationFn: ({ termId, file }: { termId: string; file: File }) =>
        unwrap(
          api.POST(`/api/catalog/${toValue(kind)}/{term_id}/image`, {
            ...path(termId),
            body: { file } as never,
            bodySerializer: () => {
              const form = new FormData()
              form.append('file', file)
              return form
            },
          }),
        ),
      onSuccess: invalidate,
    }),
    removeImage: useMutation({
      mutationFn: (termId: string) =>
        unwrap(api.DELETE(`/api/catalog/${toValue(kind)}/{term_id}/image`, path(termId))),
      onSuccess: invalidate,
    }),
    merge: useMutation({
      mutationFn: ({ termId, targetId }: { termId: string; targetId: string }) =>
        unwrap(
          api.POST(`/api/catalog/${toValue(kind)}/{term_id}/merge`, {
            ...path(termId),
            body: { target_id: targetId },
          }),
        ),
      onSuccess: invalidate,
    }),
    remove: useMutation({
      mutationFn: (termId: string) =>
        unwrap(api.DELETE(`/api/catalog/${toValue(kind)}/{term_id}`, path(termId))),
      onSuccess: invalidate,
    }),
  }
}

/** Encyclopedia entries that may describe the term, the likeliest first. */
export function useDescriptionCandidates(
  kind: MaybeRefOrGetter<DescribedKind>,
  termId: MaybeRefOrGetter<string>,
  source: MaybeRefOrGetter<string>,
  query: MaybeRefOrGetter<string>,
) {
  return useQuery({
    queryKey: computed(() => [
      'descriptions',
      toValue(kind),
      toValue(termId),
      toValue(source),
      toValue(query),
    ]),
    queryFn: () =>
      unwrap(
        api.GET(`/api/catalog/${toValue(kind)}/{term_id}/description/{source}/candidates`, {
          params: {
            path: { term_id: toValue(termId), source: toValue(source) },
            query: { q: toValue(query) },
          },
        }),
      ),
    retry: false,
  })
}

/** Take an entry's text as the description and, with `image`, its logo as the picture. */
export function useApplyDescription(kind: MaybeRefOrGetter<DescribedKind>) {
  const client = useQueryClient()
  return useMutation({
    mutationFn: ({
      termId,
      source,
      externalId,
      image,
    }: {
      termId: string
      source: string
      externalId: string
      image: boolean
    }) =>
      unwrap(
        api.POST(`/api/catalog/${toValue(kind)}/{term_id}/description/{source}`, {
          params: { path: { term_id: termId, source } },
          body: { external_id: externalId, image },
        }),
      ),
    onSuccess: () => invalidateDescribed(client, toValue(kind)),
  })
}

/** The switched-on sources that can describe this kind (none for genres). */
export function useDescribers(kind: MaybeRefOrGetter<TermKind | 'platforms'>) {
  const providers = useProviders()
  return computed(() => {
    const current = toValue(kind)
    if (!isDescribed(current)) return []
    const enabled = (providers.data.value ?? []).filter((p) => p.enabled)
    return DESCRIPTION_SOURCES[current].flatMap((name) => enabled.filter((p) => p.name === name))
  })
}

/** The pictures the entries a term is linked to offer (every logo …), as tokens. */
export function useImageCandidates(
  kind: MaybeRefOrGetter<DescribedKind>,
  termId: MaybeRefOrGetter<string>,
) {
  return useQuery({
    queryKey: computed(() => ['term-images', toValue(kind), toValue(termId)]),
    queryFn: () =>
      unwrap(
        api.GET(`/api/catalog/${toValue(kind)}/{term_id}/images`, {
          params: { path: { term_id: toValue(termId) } },
        }),
      ),
    retry: false,
  })
}

/** A picture to choose, loaded through the server. */
export const imagePreviewUrl = (token: string) =>
  `/api/catalog/term-image-preview?token=${encodeURIComponent(token)}`

/** Where a picture goes: the picture (a platform's logo), a platform's photo of the
 * device or its badge's icon. */
export type ImageTarget = 'image' | 'photo' | 'icon'

/** Pictures on Wikimedia Commons for a query (only while there is one). */
export function useCommonsImages(query: MaybeRefOrGetter<string>) {
  return useQuery({
    queryKey: computed(() => ['commons-images', toValue(query)]),
    queryFn: () =>
      unwrap(api.GET('/api/catalog/commons-images', { params: { query: { q: toValue(query) } } })),
    enabled: computed(() => !!toValue(query).trim()),
    retry: false,
  })
}

/** Make one of them the picture – or a platform's photo or badge icon. */
export function useTakeImage(kind: MaybeRefOrGetter<DescribedKind>) {
  const client = useQueryClient()
  return useMutation({
    mutationFn: ({
      termId,
      token,
      target = 'image',
    }: {
      termId: string
      token: string
      target?: ImageTarget
    }) =>
      unwrap(
        api.POST(`/api/catalog/${toValue(kind)}/{term_id}/images`, {
          params: { path: { term_id: termId } },
          body: { token, target },
        }),
      ),
    onSuccess: () => invalidateDescribed(client, toValue(kind)),
  })
}

/** Platform badges sit on releases, items and trackings: those reload too. */
function invalidateDescribed(client: ReturnType<typeof useQueryClient>, kind: DescribedKind) {
  const queries =
    kind === 'platforms'
      ? [keys.platforms, ['platform'], ['works'], ['releases'], ['items'], ['trackings']]
      : [['terms']]
  return Promise.all(
    queries.map((queryKey) => client.invalidateQueries({ queryKey: [...queryKey] })),
  )
}

const pick = (data: { name: string; image_url: string | null; description: string }) => ({
  name: data.name,
  image_url: data.image_url,
  description: data.description,
})

/** What the description and picture pages show of it: a term's or a platform's name,
 * picture and description (and a platform's badge icon). */
export function useSubject(kind: MaybeRefOrGetter<DescribedKind>, id: MaybeRefOrGetter<string>) {
  const isPlatform = computed(() => toValue(kind) === 'platforms')
  const term = useTerm(
    () => (isPlatform.value ? 'companies' : toValue(kind)) as TermKind,
    () => (isPlatform.value ? '' : toValue(id)),
  )
  const platform = usePlatform(() => (isPlatform.value ? toValue(id) : ''))
  return computed(() => {
    if (isPlatform.value) {
      const data = platform.data.value
      return data && { ...pick(data), icon_url: data.icon_url, photo_url: data.photo_url }
    }
    const data = term.data.value
    return data && { ...pick(data), icon_url: null, photo_url: null }
  })
}
