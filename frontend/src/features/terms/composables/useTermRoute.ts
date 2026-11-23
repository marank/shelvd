import { computed } from 'vue'
import { useRoute } from 'vue-router'
import type { TermKind } from '@/lib/terms'

/** The kind (from the route's meta) and id of the term page being shown; the description
 * and picture pages serve platforms too (kind "platforms", id from `platformId`). */
export function useTermRoute() {
  const route = useRoute()
  const kind = computed(() => route.meta.kind as TermKind)
  const termId = computed(() => String(route.params.termId ?? route.params.platformId ?? ''))
  return { kind, termId }
}
