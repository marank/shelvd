<script setup lang="ts" generic="T extends string">
// A native <select> styled like our inputs: the best picker on phones, fully keyboard-usable.
// Options come from the `options` prop or as <option> children in the default slot.
import { ChevronDown } from '@lucide/vue'
import { cn } from '@/lib/utils'

defineOptions({ inheritAttrs: false })
const props = defineProps<{
  options?: { value: string; label: string }[]
  class?: string
}>()
const model = defineModel<T>({ required: true })
</script>

<template>
  <div :class="cn('relative w-full min-w-0', props.class)">
    <!-- eslint-disable-next-line vuejs-accessibility/form-control-has-label -- id or aria-label come from the caller through $attrs -->
    <select
      v-model="model"
      v-bind="$attrs"
      class="h-8 w-full min-w-0 appearance-none rounded-lg border border-input bg-transparent py-1 pr-8 pl-2.5 text-base outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 disabled:cursor-not-allowed disabled:opacity-50 aria-invalid:border-destructive md:text-sm dark:bg-input/30"
    >
      <slot>
        <option v-for="option in options" :key="option.value" :value="option.value">
          {{ option.label }}
        </option>
      </slot>
    </select>
    <ChevronDown
      class="pointer-events-none absolute top-1/2 right-2.5 size-4 -translate-y-1/2 text-muted-foreground"
    />
  </div>
</template>
