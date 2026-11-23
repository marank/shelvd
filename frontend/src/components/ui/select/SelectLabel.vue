<script setup lang="ts">
import type { SelectLabelProps } from 'reka-ui'
import type { HTMLAttributes } from 'vue'
import { cn } from 'cn'
import { SelectLabel as SelectLabelPrimitive } from 'reka-ui'

const props = defineProps<SelectLabelProps & { class?: HTMLAttributes['class'] }>()
</script>

<template>
  <SelectLabelPrimitive
    data-slot="select-label"
    :class="cn('text-muted-foreground px-1.5 py-1 text-xs', props.class)"
  >
    <slot />
  </SelectLabelPrimitive>
</template>
