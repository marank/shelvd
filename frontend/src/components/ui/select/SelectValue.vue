<script setup lang="ts">
import type { SelectValueProps } from 'reka-ui'
import { SelectValue as SelectValuePrimitive } from 'reka-ui'

const props = defineProps<SelectValueProps>()
</script>

<template>
  <SelectValuePrimitive data-slot="select-value" v-bind="props">
    <slot />
  </SelectValuePrimitive>
</template>
