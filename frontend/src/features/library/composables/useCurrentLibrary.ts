import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useLibraries } from './useLibraries'

const STORAGE_KEY = 'shelvd.library'

function remembered(): string | null {
  try {
    return localStorage.getItem(STORAGE_KEY)
  } catch {
    return null
  }
}

/** The library last opened: by its URL (/l/…) or by opening one of its copies. */
const last = ref<string | null>(null)

/** A copy's page makes its library the current one (the copy belongs there). */
export function openLibrary(id: string): void {
  last.value = id
}

/** The library in the URL, else the last one opened, else the first one. Game and
 * release pages show this library's copies. */
export function useCurrentLibrary() {
  const route = useRoute()
  const libraries = useLibraries()
  const id = computed(() => {
    const fromRoute = route.params.libraryId
    if (typeof fromRoute === 'string' && fromRoute) return fromRoute
    const all = libraries.data.value ?? []
    const wanted = last.value ?? remembered()
    return all.find((l) => l.id === wanted)?.id ?? all[0]?.id ?? ''
  })
  const library = computed(() => libraries.data.value?.find((l) => l.id === id.value))
  watch(
    id,
    (value) => {
      if (!value) return
      last.value = value
      try {
        localStorage.setItem(STORAGE_KEY, value)
      } catch {
        // not remembered, that's all
      }
    },
    { immediate: true },
  )
  return { id, library, libraries }
}
