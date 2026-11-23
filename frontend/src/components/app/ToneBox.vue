<script setup lang="ts">
// The box around a picture with a transparent background (a logo, a device on white): a
// picture that would vanish on the page's background is inverted (a one-colour logo) or
// gets a fine contrasting rim along its shape – so every box keeps the same background.
// The tone comes from the server (see lib/imageTone).
import { computed, type HTMLAttributes } from 'vue'
import { rimFor } from '@/lib/imageTone'
import { cn } from '@/lib/utils'

const props = defineProps<{
  tone: string | null | undefined
  /** A photo (a device …): never inverted, only outlined. */
  photo?: boolean
  class?: HTMLAttributes['class']
}>()
const rim = computed(() => rimFor(props.tone, props.photo))
</script>

<template>
  <span :class="cn(props.class, rim)" :data-tone="tone || undefined"><slot /></span>
</template>
