<script setup lang="ts">
import { ref, watch } from 'vue'
import { Input } from '@/components/ui/input'
import { useListbox, useSuggestions, type Suggestion } from '../composables/useTerms'
import SuggestionList from './SuggestionList.vue'

/** The edition: free text (just a label of the release), with the editions already in
 * use as suggestions – so "Deluxe Edition" is spelled the same everywhere. */
const props = defineProps<{ id: string; placeholder?: string }>()
const value = defineModel<string>({ required: true })

const options = ref<Suggestion[]>([])
const { open, active, onKeydown } = useListbox(options, pick)
const suggestions = useSuggestions('editions', value, open)
watch(
  [() => suggestions.data.value, value],
  () => {
    // What's typed exactly needs no suggestion of itself.
    options.value = (suggestions.data.value ?? []).filter((s) => s.name !== value.value.trim())
    active.value = 0
  },
  { immediate: true },
)

function pick(option: Suggestion) {
  value.value = option.name
  open.value = false
}
</script>

<template>
  <div class="relative">
    <Input
      :id="id"
      v-model="value"
      role="combobox"
      autocomplete="off"
      :aria-expanded="open && options.length > 0"
      :aria-controls="`${props.id}-suggestions`"
      :placeholder="placeholder"
      @focus="open = true"
      @input="open = true"
      @blur="open = false"
      @keydown="onKeydown"
    />
    <SuggestionList
      v-if="open && options.length"
      :id="`${props.id}-suggestions`"
      :options="options"
      :active="active"
      :label="(o) => o.name"
      :uses="(o) => o.uses"
      @pick="pick"
      @highlight="(i) => (active = i)"
    />
  </div>
</template>
