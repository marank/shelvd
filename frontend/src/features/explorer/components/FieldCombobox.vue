<script setup lang="ts">
import { ChevronsUpDown } from '@lucide/vue'
import { computed, nextTick, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { FIELD_KEYS, LEVELS, fieldLevel, useFieldLabel, type ItemFieldKey } from '@/lib/itemFields'
import { cn } from '@/lib/utils'

/** Pick a field by typing: "serie", "ort.typ", "ausgabe.nummer" – suggestions grouped by
 * level, arrow keys and Enter to choose, Escape to keep the current field. */
const props = defineProps<{ id?: string }>()
const model = defineModel<ItemFieldKey>({ required: true })
const { t } = useI18n()
const label = useFieldLabel()
const open = ref(false)
const query = ref('')
const active = ref(0)
const input = ref<HTMLInputElement | null>(null)

const options = computed(() => FIELD_KEYS.filter((key) => label.matches(key, query.value)))
const grouped = computed(() =>
  LEVELS.map((level) => ({
    ...level,
    keys: options.value.filter((key) => fieldLevel(key) === level.key),
  })).filter((g) => g.keys.length),
)
/** Options in display order, for the arrow keys. */
const ordered = computed(() => grouped.value.flatMap((g) => g.keys))

function show() {
  query.value = ''
  active.value = Math.max(0, ordered.value.indexOf(model.value))
  open.value = true
}
function choose(key: ItemFieldKey) {
  model.value = key
  open.value = false
  input.value?.blur()
}
function move(by: number) {
  if (!open.value) return show()
  const count = ordered.value.length
  if (count) active.value = (active.value + by + count) % count
  void nextTick(() =>
    document
      .querySelector(`[data-option-index="${props.id}-${active.value}"]`)
      ?.scrollIntoView({ block: 'nearest' }),
  )
}
function enter() {
  const key = ordered.value[active.value]
  if (open.value && key) choose(key)
}
function onInput(value: string) {
  query.value = value
  active.value = 0
  open.value = true
}
</script>

<template>
  <div class="relative min-w-0 flex-1">
    <input
      ref="input"
      :value="open ? query : label(model)"
      :placeholder="open ? label(model) : ''"
      role="combobox"
      :aria-expanded="open"
      :aria-label="t('explorer.filterField')"
      :aria-controls="`${id}-options`"
      autocomplete="off"
      class="h-8 w-full rounded-lg border bg-transparent pr-7 pl-2.5 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 dark:bg-input/30"
      data-testid="filter-field"
      @focus="show"
      @input="onInput(($event.target as HTMLInputElement).value)"
      @keydown.down.prevent="move(1)"
      @keydown.up.prevent="move(-1)"
      @keydown.enter.prevent="enter"
      @keydown.esc.prevent="open = false"
      @blur="open = false"
    />
    <ChevronsUpDown
      class="pointer-events-none absolute top-2 right-2 size-4 text-muted-foreground"
    />
    <div
      v-if="open"
      :id="`${id}-options`"
      role="listbox"
      class="absolute top-9 left-0 z-50 max-h-72 w-full min-w-64 overflow-y-auto rounded-lg border bg-popover p-1 text-sm shadow-md"
      data-testid="field-options"
    >
      <template v-for="group in grouped" :key="group.key">
        <p
          class="flex items-center gap-1.5 px-2 pt-1.5 pb-1 font-mono text-[10px] tracking-wider text-muted-foreground uppercase"
        >
          <component :is="group.icon" class="size-3" />
          {{ t(`levels.${group.key}`) }}
        </p>
        <button
          v-for="key in group.keys"
          :key="key"
          type="button"
          role="option"
          :aria-selected="ordered.indexOf(key) === active"
          :data-option-index="`${id}-${ordered.indexOf(key)}`"
          :data-testid="`field-option-${key}`"
          :class="
            cn(
              'flex w-full items-center rounded-md px-2 py-1.5 text-left',
              ordered.indexOf(key) === active && 'bg-accent',
              key === model && 'font-medium',
            )
          "
          @mousedown.prevent="choose(key)"
          @mousemove="active = ordered.indexOf(key)"
        >
          {{ label(key) }}
        </button>
      </template>
      <p v-if="!ordered.length" class="px-2 py-1.5 text-muted-foreground">
        {{ t('explorer.noFieldMatch') }}
      </p>
    </div>
  </div>
</template>
