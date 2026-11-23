import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { computed, toValue, type MaybeRefOrGetter } from 'vue'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/schema'
import { keys } from '@/features/library/composables/queryKeys'

export type PlatformIn = components['schemas']['PlatformIn']
export type PlatformListEntry = components['schemas']['PlatformListOut']
/** The page's logo or photo of the device. */
export type PictureSlot = 'image' | 'photo'

/** One platform with its IGDB id and how many releases use it (for the edit page). */
export function usePlatform(platformId: MaybeRefOrGetter<string>) {
  return useQuery({
    queryKey: computed(() => ['platform', toValue(platformId)]),
    queryFn: () =>
      unwrap(
        api.GET('/api/catalog/platforms/{platform_id}', {
          params: { path: { platform_id: toValue(platformId) } },
        }),
      ),
    enabled: computed(() => !!toValue(platformId)),
  })
}

/** A platform's games in the catalog and what they have in common (its page). */
export function usePlatformGames(platformId: MaybeRefOrGetter<string>) {
  return useQuery({
    queryKey: computed(() => ['platform', toValue(platformId), 'games']),
    queryFn: () =>
      unwrap(
        api.GET('/api/catalog/platforms/{platform_id}/games', {
          params: { path: { platform_id: toValue(platformId) } },
        }),
      ),
    enabled: computed(() => !!toValue(platformId)),
  })
}

/** Platform badges sit on releases, items and trackings: reload all of them. */
export function usePlatformMutations() {
  const client = useQueryClient()
  const invalidate = () =>
    Promise.all(
      [keys.platforms, ['platform'], ['works'], ['releases'], ['items'], ['trackings']].map(
        (queryKey) => client.invalidateQueries({ queryKey: [...queryKey] }),
      ),
    )
  const path = (id: string) => ({ params: { path: { platform_id: id } } })
  return {
    create: useMutation({
      mutationFn: (body: PlatformIn) => unwrap(api.POST('/api/catalog/platforms', { body })),
      onSuccess: invalidate,
    }),
    update: useMutation({
      mutationFn: ({ id, body }: { id: string; body: PlatformIn }) =>
        unwrap(api.PATCH('/api/catalog/platforms/{platform_id}', { ...path(id), body })),
      onSuccess: invalidate,
    }),
    remove: useMutation({
      mutationFn: (id: string) =>
        unwrap(api.DELETE('/api/catalog/platforms/{platform_id}', path(id))),
      onSuccess: invalidate,
    }),
    uploadIcon: useMutation({
      mutationFn: ({ id, file }: { id: string; file: File }) =>
        unwrap(
          api.POST('/api/catalog/platforms/{platform_id}/icon', {
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
    }),
    uploadPicture: useMutation({
      mutationFn: ({ id, slot, file }: { id: string; slot: PictureSlot; file: File }) =>
        unwrap(
          api.POST(`/api/catalog/platforms/{platform_id}/${slot}`, {
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
    }),
    removePicture: useMutation({
      mutationFn: ({ id, slot }: { id: string; slot: PictureSlot }) =>
        unwrap(api.DELETE(`/api/catalog/platforms/{platform_id}/${slot}`, path(id))),
      onSuccess: invalidate,
    }),
    removeIcon: useMutation({
      mutationFn: (id: string) =>
        unwrap(api.DELETE('/api/catalog/platforms/{platform_id}/icon', path(id))),
      onSuccess: invalidate,
    }),
  }
}
