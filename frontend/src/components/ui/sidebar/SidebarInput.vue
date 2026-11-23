<script setup lang="ts">
import type { HTMLAttributes } from 'vue'
import { cn } from 'cn'
import { Input } from '@/components/ui/input'

const props = defineProps<{
  class?: HTMLAttributes['class']
}>()

const modelValue = defineModel<string>({ default: '' })
</script>

<template>
  <Input
    v-model="modelValue"
    data-slot="sidebar-input"
    data-sidebar="input"
    :class="cn('bg-background h-8 w-full shadow-none', props.class)"
  >
    <slot />
  </Input>
</template>
