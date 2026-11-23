<script setup lang="ts" generic="T">
import { Plus } from '@lucide/vue'
import { useI18n } from 'vue-i18n'
import { cn } from '@/lib/utils'

/** The open list under a picker: each option with how often it's used; "create" options
 * marked with a plus. Mouse-down picks (before the input's blur closes the list). */
defineProps<{
  id: string
  options: T[]
  active: number
  label: (option: T) => string
  uses?: (option: T) => number | undefined
  isCreate?: (option: T) => boolean
  loading?: boolean
}>()
const emit = defineEmits<{ pick: [option: T]; highlight: [index: number] }>()
const { t } = useI18n()
</script>

<template>
  <ul
    :id="id"
    role="listbox"
    class="absolute top-full right-0 left-0 z-50 mt-1 max-h-64 overflow-y-auto rounded-md border bg-popover p-1 text-sm text-popover-foreground shadow-md"
    :data-testid="`${id}-list`"
  >
    <!-- eslint-disable-next-line vuejs-accessibility/interactive-supports-focus -- combobox pattern: focus stays in the input, which moves through the options with aria-activedescendant -->
    <li
      v-for="(option, i) in options"
      :id="`${id}-option-${i}`"
      :key="i"
      role="option"
      :aria-selected="i === active"
      :class="
        cn(
          'flex cursor-default items-center gap-2 rounded-sm px-2 py-1.5',
          i === active && 'bg-accent text-accent-foreground',
        )
      "
      data-testid="suggestion"
      @mousedown.prevent="emit('pick', option)"
      @mousemove="emit('highlight', i)"
    >
      <Plus v-if="isCreate?.(option)" class="size-3.5 text-muted-foreground" />
      <span class="min-w-0 flex-1 truncate">{{ label(option) }}</span>
      <span
        v-if="uses?.(option) !== undefined"
        class="tabular font-mono text-[11px] text-muted-foreground"
      >
        {{ uses?.(option) }}
      </span>
    </li>
    <li v-if="!options.length" class="px-2 py-1.5 text-muted-foreground">
      {{ loading ? '…' : t('picker.none') }}
    </li>
  </ul>
</template>
