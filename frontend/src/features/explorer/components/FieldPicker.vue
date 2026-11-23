<script setup lang="ts">
import { ArrowDown, ArrowUp, GripVertical, RotateCcw, X } from '@lucide/vue'
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { Button } from '@/components/ui/button'
import { LEVELS, fieldLevel, useFieldLabel, type ItemFieldKey } from '@/lib/itemFields'
import { useReorder } from '../composables/useReorder'
import FieldChooser from './FieldChooser.vue'

/** Choose and order the fields shown per item, grouped by copy / release / game.
 * An empty selection means "the layout's defaults" (`defaults`). */
const props = defineProps<{ defaults: ItemFieldKey[] }>()
const model = defineModel<ItemFieldKey[]>({ required: true })
const { t } = useI18n()

const shown = computed(() => (model.value.length ? model.value : props.defaults))
const usingDefaults = computed(() => !model.value.length)
const label = useFieldLabel()

function toggle(key: ItemFieldKey) {
  model.value = shown.value.includes(key)
    ? shown.value.filter((k) => k !== key)
    : [...shown.value, key]
}
// Reordering starts from what is shown (the defaults, too) and saves into the model.
const order = computed({ get: () => shown.value, set: (keys) => (model.value = keys) })
const { dragging, drop, move } = useReorder(order)
const levelIcon = (key: ItemFieldKey) => LEVELS.find((l) => l.key === fieldLevel(key))!.icon
</script>

<template>
  <div class="grid gap-5 md:grid-cols-[1fr_19rem]" data-testid="field-picker">
    <FieldChooser :selected="shown" :exclude="['game.title']" @toggle="toggle" />
    <div
      class="md:-my-1 md:h-[26.5rem] md:overflow-x-hidden md:overflow-y-auto md:border-l md:py-1 md:pr-1 md:pl-6"
    >
      <div class="mb-2 flex h-7 items-center gap-2">
        <span class="font-mono text-[11px] tracking-wider text-muted-foreground uppercase">
          {{ t('explorer.shownFields') }}
        </span>
        <span
          v-if="usingDefaults"
          class="rounded-sm border px-1.5 py-px text-[10px] text-muted-foreground"
          data-testid="default-badge"
        >
          {{ t('explorer.resetFields') }}
        </span>
        <Button
          v-else
          type="button"
          variant="ghost"
          size="sm"
          class="ml-auto h-7 px-2 text-xs"
          data-testid="reset-fields"
          @click="model = []"
        >
          <RotateCcw class="size-3" /> {{ t('explorer.resetFields') }}
        </Button>
      </div>
      <ol class="grid gap-1.5" data-testid="shown-fields">
        <!-- eslint-disable-next-line vuejs-accessibility/no-static-element-interactions -- dragging is a pointer shortcut; the row's move buttons do the same by keyboard -->
        <li
          v-for="(key, index) in shown"
          :key="key"
          draggable="true"
          class="group/row flex h-9 items-center gap-2 rounded-md border bg-card pr-1 pl-1.5 text-sm"
          :class="dragging === index && 'opacity-50'"
          @dragstart="dragging = index"
          @dragend="dragging = null"
          @dragover.prevent
          @drop="drop(index)"
        >
          <GripVertical class="size-4 shrink-0 cursor-grab text-muted-foreground/60" />
          <component :is="levelIcon(key)" class="size-3.5 shrink-0 text-muted-foreground" />
          <span class="min-w-0 flex-1 truncate">{{ label(key) }}</span>
          <span
            class="flex opacity-0 transition-opacity group-hover/row:opacity-100 focus-within:opacity-100"
          >
            <Button
              type="button"
              variant="ghost"
              size="icon-sm"
              class="size-7"
              :disabled="index === 0"
              :aria-label="t('explorer.moveUp')"
              @click="move(index, -1)"
            >
              <ArrowUp class="size-3.5" />
            </Button>
            <Button
              type="button"
              variant="ghost"
              size="icon-sm"
              class="size-7"
              :disabled="index === shown.length - 1"
              :aria-label="t('explorer.moveDown')"
              data-testid="move-down"
              @click="move(index, 1)"
            >
              <ArrowDown class="size-3.5" />
            </Button>
          </span>
          <Button
            type="button"
            variant="ghost"
            size="icon-sm"
            class="size-7"
            :aria-label="t('actions.hide')"
            data-testid="hide-field"
            @click="toggle(key)"
          >
            <X class="size-3.5" />
          </Button>
        </li>
      </ol>
    </div>
  </div>
</template>
