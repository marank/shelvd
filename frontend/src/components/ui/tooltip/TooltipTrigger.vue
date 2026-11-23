<script setup lang="ts">
import type { TooltipTriggerProps } from 'reka-ui'
import { TooltipTrigger as TooltipTriggerPrimitive } from 'reka-ui'

const props = defineProps<TooltipTriggerProps>()
</script>

<template>
  <TooltipTriggerPrimitive data-slot="tooltip-trigger" v-bind="props">
    <slot />
  </TooltipTriggerPrimitive>
</template>
