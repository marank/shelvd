<script setup lang="ts">
import { onBeforeUnmount, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { cn } from '@/lib/utils'

/**
 * A vertical drag handle that resizes a neighbouring panel. `edge` says which edge of
 * the panel it sits on: "right" for a left-hand panel (drag right = wider), "left" for a
 * right-hand panel (drag left = wider). Keyboard: ←/→ by 16 px; double-click resets.
 */
const props = defineProps<{
  min: number
  max: number
  defaultWidth: number
  edge: 'left' | 'right'
  label: string
  class?: string
}>()
const width = defineModel<number>({ required: true })
const emit = defineEmits<{ dragging: [active: boolean] }>()
const { t } = useI18n()
const active = ref(false)
let startX = 0
let startWidth = 0

const clamp = (value: number) => Math.round(Math.min(props.max, Math.max(props.min, value)))

function onMove(event: PointerEvent) {
  const delta = event.clientX - startX
  width.value = clamp(startWidth + (props.edge === 'right' ? delta : -delta))
}

function stop() {
  active.value = false
  emit('dragging', false)
  document.body.style.removeProperty('cursor')
  document.body.style.removeProperty('user-select')
  window.removeEventListener('pointermove', onMove)
  window.removeEventListener('pointerup', stop)
}

function start(event: PointerEvent) {
  if (event.button !== 0) return
  event.preventDefault()
  startX = event.clientX
  startWidth = width.value
  active.value = true
  emit('dragging', true)
  // While dragging, the whole page shows the resize cursor and text isn't selected.
  document.body.style.cursor = 'col-resize'
  document.body.style.userSelect = 'none'
  window.addEventListener('pointermove', onMove)
  window.addEventListener('pointerup', stop)
}

function onKey(event: KeyboardEvent) {
  const step = event.shiftKey ? 64 : 16
  const grow = props.edge === 'right' ? 'ArrowRight' : 'ArrowLeft'
  const shrink = props.edge === 'right' ? 'ArrowLeft' : 'ArrowRight'
  if (event.key === grow) width.value = clamp(width.value + step)
  else if (event.key === shrink) width.value = clamp(width.value - step)
  else if (event.key === 'Home') width.value = props.min
  else if (event.key === 'End') width.value = props.max
  else return
  event.preventDefault()
}

onBeforeUnmount(stop)
</script>

<template>
  <!-- eslint-disable-next-line vuejs-accessibility/no-static-element-interactions -- a focusable separator is an ARIA widget (arrow keys resize); the rule only knows static separators -->
  <div
    role="separator"
    aria-orientation="vertical"
    tabindex="0"
    :aria-label="label"
    :aria-valuemin="min"
    :aria-valuemax="max"
    :aria-valuenow="width"
    :title="t('layout.resizeHint')"
    data-testid="resize-handle"
    :class="
      cn(
        'group/resize absolute inset-y-0 z-20 hidden w-2 cursor-col-resize touch-none outline-none md:block',
        edge === 'right' ? '-right-1' : '-left-1',
        props.class,
      )
    "
    @pointerdown="start"
    @dblclick="width = defaultWidth"
    @keydown="onKey"
  >
    <span
      :class="
        cn(
          'absolute inset-y-0 left-1/2 w-px -translate-x-1/2 bg-transparent transition-colors group-hover/resize:bg-primary/50 group-focus-visible/resize:bg-primary',
          active && 'w-0.5 bg-primary',
        )
      "
    />
  </div>
</template>
