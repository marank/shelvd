<script setup lang="ts">
import type { PopoverAnchorProps } from 'reka-ui'
import { PopoverAnchor as PopoverAnchorPrimitive } from 'reka-ui'

const props = defineProps<PopoverAnchorProps>()
</script>

<template>
  <PopoverAnchorPrimitive data-slot="popover-anchor" v-bind="props">
    <slot />
  </PopoverAnchorPrimitive>
</template>
