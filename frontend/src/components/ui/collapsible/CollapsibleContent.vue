<script setup lang="ts">
import type { CollapsibleContentProps } from 'reka-ui'
import { CollapsibleContent as CollapsibleContentPrimitive } from 'reka-ui'

const props = defineProps<CollapsibleContentProps>()
</script>

<template>
  <CollapsibleContentPrimitive data-slot="collapsible-content" v-bind="props">
    <slot />
  </CollapsibleContentPrimitive>
</template>
