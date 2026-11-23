<script setup lang="ts">
import { computed } from 'vue'
import { richText } from '@/lib/richText'

/** A description with its simple formatting (lists, bold), sanitized. */
const props = defineProps<{ text: string }>()
const html = computed(() => richText(props.text))
</script>

<template>
  <!-- eslint-disable vue/no-v-html -- sanitized by richText() -->
  <div
    class="whitespace-pre-line [&_b]:font-semibold [&_b]:text-foreground [&_li]:my-0.5 [&_ol]:my-2 [&_ol]:list-decimal [&_ol]:pl-5 [&_p]:my-2 [&_strong]:font-semibold [&_strong]:text-foreground [&_ul]:my-2 [&_ul]:list-disc [&_ul]:pl-5"
    v-html="html"
  />
  <!-- eslint-enable vue/no-v-html -->
</template>
