<script setup lang="ts">
import type { TooltipProviderProps } from 'reka-ui'
import { TooltipProvider as TooltipProviderPrimitive } from 'reka-ui'

const props = withDefaults(defineProps<TooltipProviderProps>(), {
  delayDuration: 0,
})
</script>

<template>
  <TooltipProviderPrimitive v-bind="props">
    <slot />
  </TooltipProviderPrimitive>
</template>
