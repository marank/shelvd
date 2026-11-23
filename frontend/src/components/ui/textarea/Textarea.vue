<script setup lang="ts" generic="T extends string | number">
import type { HTMLAttributes } from 'vue'
import { cn } from 'cn'
import { computed } from 'vue'

// Generic, so v-model keeps the bound value's type (string or number) under strictTemplates.
const props = defineProps<{
  modelValue?: T
  class?: HTMLAttributes['class']
}>()

const emit = defineEmits<{
  'update:modelValue': [payload: T]
}>()

const modelValue = computed({
  get: () => props.modelValue,
  // The element hands back what was typed; a `.number` modifier on the parent's v-model converts it.
  set: (value) => emit('update:modelValue', value as T),
})
</script>

<template>
  <!-- eslint-disable-next-line vuejs-accessibility/form-control-has-label -- id or aria-label come from the caller as fallthrough attributes -->
  <textarea
    v-model="modelValue"
    data-slot="textarea"
    :class="
      cn(
        'border-input dark:bg-input/30 focus-visible:border-ring focus-visible:ring-ring/50 aria-invalid:ring-destructive/20 dark:aria-invalid:ring-destructive/40 aria-invalid:border-destructive dark:aria-invalid:border-destructive/50 disabled:bg-input/50 dark:disabled:bg-input/80 rounded-lg border bg-transparent px-2.5 py-2 text-base transition-colors focus-visible:ring-3 aria-invalid:ring-3 md:text-sm flex field-sizing-content min-h-16 w-full outline-none placeholder:text-muted-foreground disabled:cursor-not-allowed disabled:opacity-50',
        props.class,
      )
    "
  />
</template>
