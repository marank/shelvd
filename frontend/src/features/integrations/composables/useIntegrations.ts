import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { computed, toValue, type MaybeRefOrGetter } from 'vue'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { keys } from '@/features/library/composables/queryKeys'

/** Admins: every integration with its settings (secrets only masked). */
export function useIntegrations(enabled: MaybeRefOrGetter<boolean> = true) {
  return useQuery({
    queryKey: ['integrations'],
    queryFn: () => unwrap(api.GET('/api/integrations')),
    enabled: computed(() => toValue(enabled)),
  })
}

export interface IntegrationChanges {
  enabled?: boolean
  options?: Record<string, unknown>
  /** Only the ones sent change; "" removes one. */
  secrets?: Record<string, string>
}

export function useSaveIntegration() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: ({ key, body }: { key: string; body: IntegrationChanges }) =>
      unwrap(api.PATCH('/api/integrations/{key}', { params: { path: { key } }, body })),
    onSuccess: () =>
      Promise.all([
        client.invalidateQueries({ queryKey: ['integrations'] }),
        client.invalidateQueries({ queryKey: keys.providers }),
      ]),
  })
}

export function useTestIntegration() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: (key: string) =>
      unwrap(api.POST('/api/integrations/{key}/test', { params: { path: { key } } })),
    onSettled: () => client.invalidateQueries({ queryKey: ['integrations'] }),
  })
}
