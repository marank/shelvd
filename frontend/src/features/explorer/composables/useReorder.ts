import { ref, type Ref } from 'vue'

/** Reorder a list by dragging a row onto another, or by moving one up or down. */
export function useReorder<T>(list: Ref<T[]>) {
  const dragging = ref<number | null>(null)
  function move(index: number, by: number) {
    const next = [...list.value]
    const [entry] = next.splice(index, 1)
    next.splice(index + by, 0, entry as T)
    list.value = next
  }
  function drop(index: number) {
    if (dragging.value !== null && dragging.value !== index)
      move(dragging.value, index - dragging.value)
    dragging.value = null
  }
  return { dragging, move, drop }
}
