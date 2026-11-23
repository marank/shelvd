<script setup lang="ts">
import { X } from '@lucide/vue'
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import {
  useListbox,
  useSuggestions,
  type PickedTerm,
  type Suggestion,
  type TermKind,
} from '../composables/useTerms'
import SuggestionList from './SuggestionList.vue'

/**
 * Picks catalog terms (companies, genres, series) with suggestions while typing: picked
 * ones show as chips, a name nobody has yet can be created ("„xyz“ anlegen" – created on
 * save). `multiple` allows several (developers, genres, series), else one (publisher).
 */
const props = defineProps<{
  id: string
  kind: TermKind
  multiple?: boolean
  placeholder?: string
  /** Only existing terms (no "create"), e.g. picking a merge target. */
  existingOnly?: boolean
  /** Ids never suggested (the term itself when merging). */
  exclude?: string[]
}>()
const picked = defineModel<PickedTerm[]>({ required: true })
const { t } = useI18n()

type Option = { suggestion: Suggestion } | { create: string }
const query = ref('')
const options = ref<Option[]>([])
const { open, active, onKeydown } = useListbox(options, pick)
const suggestions = useSuggestions(() => props.kind, query, open)

const same = (a: string, b: string) => a.trim().toLowerCase() === b.trim().toLowerCase()
const isPicked = (s: Suggestion) =>
  picked.value.some((p) => (!!p.id && p.id === s.id) || same(p.name, s.name))
watch(
  [() => suggestions.data.value, query, picked],
  () => {
    const typed = query.value.trim()
    const found = (suggestions.data.value ?? []).filter(
      (s) => !isPicked(s) && !props.exclude?.includes(s.id ?? ''),
    )
    const known = [...(suggestions.data.value ?? []), ...picked.value].some((s) =>
      same(s.name, typed),
    )
    options.value = [
      ...found.map((suggestion) => ({ suggestion })),
      ...(typed && !known && !props.existingOnly ? [{ create: typed }] : []),
    ]
    active.value = 0
  },
  { deep: true, immediate: true },
)

function pick(option: Option) {
  const term =
    'create' in option
      ? { name: option.create }
      : { id: option.suggestion.id, name: option.suggestion.name }
  picked.value = props.multiple ? [...picked.value, term] : [term]
  query.value = ''
  if (!props.multiple) open.value = false
}
function remove(index: number) {
  picked.value = picked.value.filter((_, i) => i !== index)
}
function keydown(event: KeyboardEvent) {
  if (event.key === 'Backspace' && !query.value && picked.value.length) {
    remove(picked.value.length - 1)
    return
  }
  onKeydown(event)
}

const label = (o: Option) =>
  'create' in o ? t('picker.create', { name: o.create }) : o.suggestion.name
const uses = (o: Option) => ('create' in o ? undefined : o.suggestion.uses)
const isCreate = (o: Option) => 'create' in o
const listId = computed(() => `${props.id}-suggestions`)
</script>

<template>
  <div class="relative">
    <div
      :class="
        cn(
          'flex min-h-9 w-full flex-wrap items-center gap-1 rounded-md border border-input bg-transparent px-2 py-1 shadow-xs dark:bg-input/30',
          'focus-within:border-ring focus-within:ring-[3px] focus-within:ring-ring/50',
        )
      "
      :data-testid="`${id}-picker`"
    >
      <Badge
        v-for="(term, i) in picked"
        :key="term.id ?? `new-${term.name}`"
        variant="secondary"
        class="gap-1 pr-1"
        data-testid="picked"
      >
        {{ term.name }}
        <button
          type="button"
          class="rounded-sm text-muted-foreground hover:text-foreground"
          :aria-label="t('picker.remove', { name: term.name })"
          @click="remove(i)"
        >
          <X class="size-3" />
        </button>
      </Badge>
      <input
        :id="id"
        v-model="query"
        role="combobox"
        autocomplete="off"
        :aria-expanded="open"
        :aria-controls="listId"
        :aria-activedescendant="open && options.length ? `${listId}-option-${active}` : undefined"
        :placeholder="picked.length ? '' : placeholder"
        class="h-7 min-w-24 flex-1 bg-transparent text-base outline-none placeholder:text-muted-foreground md:text-sm"
        @focus="open = true"
        @input="open = true"
        @blur="open = false"
        @keydown="keydown"
      />
    </div>
    <SuggestionList
      v-if="open"
      :id="listId"
      :options="options"
      :active="active"
      :label="label"
      :uses="uses"
      :is-create="isCreate"
      :loading="suggestions.isFetching.value"
      @pick="pick"
      @highlight="(i) => (active = i)"
    />
  </div>
</template>
