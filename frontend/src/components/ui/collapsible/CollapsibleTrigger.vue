<script setup lang="ts">
import type { CollapsibleTriggerProps } from 'reka-ui'
import { CollapsibleTrigger as CollapsibleTriggerPrimitive } from 'reka-ui'

const props = defineProps<CollapsibleTriggerProps>()
</script>

<template>
  <CollapsibleTriggerPrimitive data-slot="collapsible-trigger" v-bind="props">
    <slot />
  </CollapsibleTriggerPrimitive>
</template>
