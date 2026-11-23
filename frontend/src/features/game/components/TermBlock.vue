<script setup lang="ts">
// A series or company under the cover: its name, and its logo once the term is loaded.
import type { TermKind } from '@/lib/terms'
import { useTerm } from '@/features/terms/composables/useTermPages'
import AboutBlock from './AboutBlock.vue'

const props = defineProps<{ kind: TermKind; id: string; name: string; label: string }>()
const term = useTerm(
  () => props.kind,
  () => props.id,
)
</script>

<template>
  <AboutBlock
    :label="label"
    :name="name"
    :to="{ name: `${kind}-detail`, params: { termId: id } }"
    :image="term.data.value?.image_url"
    :tone="term.data.value?.image_tone"
  />
</template>
