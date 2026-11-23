import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { computed } from 'vue'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { useAuthStore } from '@/stores/auth'

const KEY = ['catalog-review'] as const

/** What people entered themselves and no admin has checked yet (admins only). */
export function useReviewQueue() {
  return useQuery({
    queryKey: KEY,
    queryFn: () => unwrap(api.GET('/api/catalog/review')),
  })
}

/** For the sidebar badge; asked only by admins. */
export function useReviewCount() {
  const auth = useAuthStore()
  return useQuery({
    queryKey: [...KEY, 'count'],
    queryFn: () => unwrap(api.GET('/api/catalog/review/count')),
    enabled: computed(() => auth.isAdmin),
    staleTime: 60_000,
  })
}

export function useReviewActions() {
  const client = useQueryClient()
  const refresh = () => client.invalidateQueries({ queryKey: KEY })
  const approve = useMutation({
    mutationFn: (body: { works?: string[]; releases?: string[]; barcodes?: string[] }) =>
      unwrap(api.POST('/api/catalog/review/approve', { body })),
    onSuccess: refresh,
  })
  const removeBarcode = useMutation({
    mutationFn: (id: string) =>
      unwrap(
        api.DELETE('/api/catalog/barcodes/{barcode_id}', { params: { path: { barcode_id: id } } }),
      ),
    onSuccess: refresh,
  })
  return { approve, removeBarcode }
}
