<script setup lang="ts">
import type { SelectItemTextProps } from 'reka-ui'
import { SelectItemText as SelectItemTextPrimitive } from 'reka-ui'

const props = defineProps<SelectItemTextProps>()
</script>

<template>
  <SelectItemTextPrimitive data-slot="select-item-text" v-bind="props">
    <slot />
  </SelectItemTextPrimitive>
</template>
