import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useProviders } from '@/features/library/composables/useReference'
import { backTarget } from '@/features/works/composables/form'
import { useWork } from '@/features/works/composables/useWork'

/** What the pages matching a game with a source share: the game and source from the route,
 * the source's name, the way back and the search box (typed text → query on submit). */
export function useMatchPage() {
  const route = useRoute()
  const router = useRouter()
  const workId = computed(() => String(route.params.workId))
  const source = computed(() => String(route.params.source))
  const work = useWork(workId)
  const providers = useProviders()
  const label = computed(
    () => providers.data.value?.find((p) => p.name === source.value)?.label ?? source.value,
  )
  const back = computed(() => backTarget(route.query.back))
  const typed = ref('')
  const query = ref('')
  function search() {
    query.value = typed.value.trim()
  }
  return { route, router, workId, source, work, providers, label, back, typed, query, search }
}
