<script setup lang="ts">
import { ChevronRight, GripVertical, Plus, X } from '@lucide/vue'
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { GROUP_FIELDS, type GroupField } from '@/api/types'
import { useFieldLabel } from '@/lib/itemFields'

const props = defineProps<{ modelValue: GroupField[] }>()
const emit = defineEmits<{ 'update:modelValue': [value: GroupField[]] }>()
const { t } = useI18n()
const label = useFieldLabel()

const available = computed(() => GROUP_FIELDS.filter((f) => !props.modelValue.includes(f)))
const dragging = ref<number | null>(null)

function remove(index: number) {
  emit(
    'update:modelValue',
    props.modelValue.filter((_, i) => i !== index),
  )
}

function add(field: GroupField) {
  emit('update:modelValue', [...props.modelValue, field])
}

/** Move a level: drag and drop with the mouse, or Alt+←/→ from the keyboard. */
function move(from: number, to: number) {
  if (to < 0 || to >= props.modelValue.length || from === to) return
  const next = [...props.modelValue]
  const [field] = next.splice(from, 1)
  next.splice(to, 0, field as GroupField)
  emit('update:modelValue', next)
}

function drop(index: number) {
  if (dragging.value !== null) move(dragging.value, index)
  dragging.value = null
}
</script>

<template>
  <div class="flex min-w-0 flex-wrap items-center gap-1" data-testid="group-by-editor">
    <span class="mr-1 font-mono text-[11px] tracking-wider text-muted-foreground uppercase">
      {{ t('explorer.nesting') }}
    </span>
    <template v-for="(field, index) in modelValue" :key="field">
      <ChevronRight v-if="index > 0" class="size-3.5 text-muted-foreground/60" />
      <!-- eslint-disable-next-line vuejs-accessibility/no-static-element-interactions -- dragging is a pointer shortcut; the focusable chip moves with Alt+arrows and goes with Delete -->
      <span
        draggable="true"
        class="group/chip inline-flex h-7 items-center gap-0.5 rounded-md border bg-card pr-0.5 pl-1 text-xs font-medium shadow-xs focus-visible:ring-[3px] focus-visible:ring-ring/40 focus-visible:outline-none"
        :class="dragging === index && 'opacity-50'"
        tabindex="0"
        :aria-label="label(field)"
        @dragstart="dragging = index"
        @dragend="dragging = null"
        @dragover.prevent
        @drop.prevent="drop(index)"
        @keydown.alt.left.prevent="move(index, index - 1)"
        @keydown.alt.right.prevent="move(index, index + 1)"
        @keydown.delete.prevent="remove(index)"
      >
        <GripVertical class="size-3 cursor-grab text-muted-foreground/60" />
        {{ label(field) }}
        <button
          type="button"
          class="ml-0.5 rounded p-0.5 text-muted-foreground hover:bg-muted hover:text-foreground"
          :aria-label="`${t('actions.delete')}: ${label(field)}`"
          :data-testid="`remove-${field}`"
          @click="remove(index)"
        >
          <X class="size-3" />
        </button>
      </span>
    </template>
    <DropdownMenu v-if="available.length">
      <DropdownMenuTrigger as-child>
        <button
          type="button"
          data-testid="add-level"
          class="inline-flex h-7 items-center gap-1 rounded-md border border-dashed px-2 text-xs text-muted-foreground hover:border-solid hover:bg-muted hover:text-foreground"
        >
          <Plus class="size-3.5" />
          {{ modelValue.length ? t('explorer.addLevel') : t('explorer.groupBy') }}
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start" class="max-h-80 w-52 overflow-y-auto">
        <DropdownMenuItem
          v-for="field in available"
          :key="field"
          :data-testid="`level-${field}`"
          @select="add(field)"
        >
          {{ label(field) }}
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  </div>
</template>
