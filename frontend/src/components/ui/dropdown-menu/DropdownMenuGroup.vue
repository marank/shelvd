<script setup lang="ts">
import type { DropdownMenuGroupProps } from 'reka-ui'
import { DropdownMenuGroup as DropdownMenuGroupPrimitive } from 'reka-ui'

const props = defineProps<DropdownMenuGroupProps>()
</script>

<template>
  <DropdownMenuGroupPrimitive data-slot="dropdown-menu-group" v-bind="props">
    <slot />
  </DropdownMenuGroupPrimitive>
</template>
