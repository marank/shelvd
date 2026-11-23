<script setup lang="ts">
import type { DialogCloseProps } from 'reka-ui'
import { DialogClose as DialogClosePrimitive } from 'reka-ui'

const props = defineProps<DialogCloseProps>()
</script>

<template>
  <DialogClosePrimitive data-slot="dialog-close" v-bind="props">
    <slot />
  </DialogClosePrimitive>
</template>
