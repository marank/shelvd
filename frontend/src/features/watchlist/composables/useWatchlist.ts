import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { computed, toValue, type MaybeRefOrGetter } from 'vue'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { Release, TakeOverIn, Tracking, TrackingIn, TrackingPatch } from '@/api/types'
import { keys } from '@/features/library/composables/queryKeys'
import { allValues } from '@/utils/enums'

export type TrackingStatus = Tracking['status']
export const TRACKING_STATUSES = allValues<TrackingStatus>({
  watching: true,
  preordered: true,
  bought: true,
})

/** Own entries only, or also the ones other members aimed at my libraries. */
export function useTrackings(mine: MaybeRefOrGetter<boolean>) {
  return useQuery({
    queryKey: computed(() => [...keys.trackings, toValue(mine) ? 'mine' : 'all']),
    queryFn: () =>
      unwrap(api.GET('/api/watchlist', { params: { query: { mine: toValue(mine) } } })),
  })
}

/** My entries; shared by every WatchButton on a page (one request). */
export function useMyTrackings() {
  return useTrackings(true)
}

export function useTracking(id: MaybeRefOrGetter<string>) {
  return useQuery({
    queryKey: computed(() => [...keys.trackings, 'one', toValue(id)]),
    queryFn: () =>
      unwrap(
        api.GET('/api/watchlist/{tracking_id}', {
          params: { path: { tracking_id: toValue(id) } },
        }),
      ),
    enabled: computed(() => !!toValue(id)),
  })
}

/** A catalog release (for "track this release" before an entry exists). */
export function useRelease(id: MaybeRefOrGetter<string>) {
  return useQuery({
    queryKey: computed(() => ['releases', toValue(id)]),
    queryFn: () =>
      unwrap(
        api.GET('/api/catalog/releases/{release_id}', {
          params: { path: { release_id: toValue(id) } },
        }),
      ),
    enabled: computed(() => !!toValue(id)),
  })
}

function useInvalidateTrackings() {
  const client = useQueryClient()
  return () => client.invalidateQueries({ queryKey: keys.trackings })
}

export function useCreateTracking() {
  const invalidate = useInvalidateTrackings()
  return useMutation({
    mutationFn: (body: Partial<TrackingIn> & Pick<TrackingIn, 'release_id'>) =>
      unwrap(
        api.POST('/api/watchlist', {
          body: { status: 'watching', shop: '', notes: '', ...body },
        }),
      ),
    onSuccess: invalidate,
  })
}

export function useUpdateTracking() {
  const invalidate = useInvalidateTrackings()
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: TrackingPatch }) =>
      unwrap(
        api.PATCH('/api/watchlist/{tracking_id}', {
          params: { path: { tracking_id: id } },
          body,
        }),
      ),
    onSuccess: invalidate,
  })
}

export type ReleaseDateFields = Pick<
  Release,
  'release_precision' | 'release_date' | 'release_date_end'
>

/** Change a release's date from its Upcoming entry (it's catalog data: for everyone). */
export function useUpdateReleaseDate() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: ({ id, date }: { id: string; date: ReleaseDateFields }) =>
      unwrap(
        api.PATCH('/api/catalog/releases/{release_id}', {
          params: { path: { release_id: id } },
          body: date,
        }),
      ),
    onSuccess: () =>
      Promise.all(
        [keys.trackings, ['works'], ['releases'], ['items']].map((queryKey) =>
          client.invalidateQueries({ queryKey }),
        ),
      ),
  })
}

export function useDeleteTracking() {
  const invalidate = useInvalidateTrackings()
  return useMutation({
    mutationFn: (id: string) =>
      unwrap(api.DELETE('/api/watchlist/{tracking_id}', { params: { path: { tracking_id: id } } })),
    onSuccess: invalidate,
  })
}

/** The game arrived: turn the entry into a copy in a library. */
export function useTakeOver() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: TakeOverIn }) =>
      unwrap(
        api.POST('/api/watchlist/{tracking_id}/take-over', {
          params: { path: { tracking_id: id } },
          body,
        }),
      ),
    onSuccess: (_item, { body }) =>
      Promise.all([
        client.invalidateQueries({ queryKey: keys.trackings }),
        client.invalidateQueries({ queryKey: keys.items(body.library_id) }),
        client.invalidateQueries({ queryKey: keys.tree(body.library_id) }),
        client.invalidateQueries({ queryKey: keys.libraries }),
      ]),
  })
}
