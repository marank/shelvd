<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import type { Release } from '@/api/types'
import { formatReleaseDate, relativeHint } from '@/lib/releaseDate'

const props = defineProps<{
  release: Pick<Release, 'release_date' | 'release_date_end' | 'release_precision'>
  /** Show "in 3 weeks" under the date. */
  hint?: boolean
}>()
const { t, locale } = useI18n()
const label = computed(() => formatReleaseDate(props.release, locale.value, t('dates.tba')))
const relative = computed(() => (props.hint ? relativeHint(props.release, locale.value) : ''))
</script>

<template>
  <span v-if="label" class="inline-flex flex-col">
    <span class="tabular font-mono">{{ label }}</span>
    <span v-if="relative" class="text-xs text-muted-foreground" data-testid="relative-hint">
      {{ relative }}
    </span>
  </span>
</template>
