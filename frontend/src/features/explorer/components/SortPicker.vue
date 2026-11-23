<script setup lang="ts">
import {
  ArrowDown,
  ArrowDownWideNarrow,
  ArrowUp,
  ArrowUpNarrowWide,
  GripVertical,
  RotateCcw,
  X,
} from '@lucide/vue'
import { useI18n } from 'vue-i18n'
import { Button } from '@/components/ui/button'
import {
  LEVELS,
  MAX_SORT_LEVELS,
  fieldLevel,
  useFieldLabel,
  type ItemFieldKey,
  type SortLevel,
} from '@/lib/itemFields'
import { useReorder } from '../composables/useReorder'
import FieldChooser from './FieldChooser.vue'

/** Choose a view's sort: up to five levels, any field or the title, each ascending or
 * descending. Empty = by title. Looks and works like the field picker. */
const model = defineModel<SortLevel[]>({ required: true })
const { t } = useI18n()

function toggle(key: ItemFieldKey) {
  model.value = model.value.some((l) => l.key === key)
    ? model.value.filter((l) => l.key !== key)
    : [...model.value, { key, desc: false }]
}
function flip(index: number) {
  model.value = model.value.map((l, i) => (i === index ? { ...l, desc: !l.desc } : l))
}
const { dragging, drop, move } = useReorder(model)
const levelIcon = (key: ItemFieldKey) => LEVELS.find((l) => l.key === fieldLevel(key))!.icon
const label = useFieldLabel()
</script>

<template>
  <div class="grid gap-5 md:grid-cols-[1fr_19rem]" data-testid="sort-picker">
    <FieldChooser
      :selected="model.map((l) => l.key)"
      :full="model.length >= MAX_SORT_LEVELS"
      @toggle="toggle"
    />
    <div
      class="md:-my-1 md:h-[26.5rem] md:overflow-x-hidden md:overflow-y-auto md:border-l md:py-1 md:pr-1 md:pl-6"
    >
      <div class="mb-2 flex h-7 items-center gap-2">
        <span class="font-mono text-[11px] tracking-wider text-muted-foreground uppercase">
          {{ t('explorer.sortLevels') }}
        </span>
        <span class="font-mono text-[11px] text-muted-foreground tabular">
          {{ model.length }}/{{ MAX_SORT_LEVELS }}
        </span>
        <Button
          v-if="model.length"
          type="button"
          variant="ghost"
          size="sm"
          class="ml-auto h-7 px-2 text-xs"
          data-testid="reset-sort"
          @click="model = []"
        >
          <RotateCcw class="size-3" /> {{ t('explorer.resetFields') }}
        </Button>
      </div>
      <p
        v-if="!model.length"
        class="rounded-md border border-dashed p-3 text-sm text-muted-foreground"
      >
        {{ t('explorer.sortDefault') }}
      </p>
      <ol class="grid gap-1.5" data-testid="sort-levels">
        <!-- eslint-disable-next-line vuejs-accessibility/no-static-element-interactions -- dragging is a pointer shortcut; the row's move buttons do the same by keyboard -->
        <li
          v-for="(level, index) in model"
          :key="level.key"
          draggable="true"
          class="flex h-9 items-center gap-2 rounded-md border bg-card pr-1 pl-1.5 text-sm"
          :class="dragging === index && 'opacity-50'"
          @dragstart="dragging = index"
          @dragend="dragging = null"
          @dragover.prevent
          @drop="drop(index)"
        >
          <GripVertical class="size-4 shrink-0 cursor-grab text-muted-foreground/60" />
          <span class="w-4 shrink-0 font-mono text-[11px] text-muted-foreground tabular">
            {{ index + 1 }}
          </span>
          <component :is="levelIcon(level.key)" class="size-3.5 shrink-0 text-muted-foreground" />
          <span class="min-w-0 flex-1 truncate">{{ label(level.key) }}</span>
          <Button
            type="button"
            variant="ghost"
            size="icon-sm"
            class="size-7"
            :disabled="index === 0"
            :aria-label="t('explorer.moveUp')"
            data-testid="sort-up"
            @click="move(index, -1)"
          >
            <ArrowUp class="size-3.5" />
          </Button>
          <Button
            type="button"
            variant="ghost"
            size="icon-sm"
            class="size-7"
            :disabled="index === model.length - 1"
            :aria-label="t('explorer.moveDown')"
            data-testid="sort-down"
            @click="move(index, 1)"
          >
            <ArrowDown class="size-3.5" />
          </Button>
          <Button
            type="button"
            variant="ghost"
            size="sm"
            class="h-7 gap-1 px-1.5 text-xs text-muted-foreground"
            :aria-label="t(level.desc ? 'explorer.descending' : 'explorer.ascending')"
            :title="t(level.desc ? 'explorer.descending' : 'explorer.ascending')"
            data-testid="flip-sort"
            @click="flip(index)"
          >
            <ArrowDownWideNarrow v-if="level.desc" class="size-4" />
            <ArrowUpNarrowWide v-else class="size-4" />
          </Button>
          <Button
            type="button"
            variant="ghost"
            size="icon-sm"
            class="size-7"
            :aria-label="t('actions.remove')"
            data-testid="remove-sort"
            @click="toggle(level.key)"
          >
            <X class="size-3.5" />
          </Button>
        </li>
      </ol>
    </div>
  </div>
</template>
