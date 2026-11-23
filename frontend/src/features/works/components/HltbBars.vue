<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import type { Release } from '@/api/types'

/** How long the game takes (HowLongToBeat): story, with extras, everything – as bars
 * relative to the longest. Nothing without those facts. */
const props = defineProps<{ release: Release }>()
const { t, n } = useI18n()
const rows = computed(() => {
  const values = props.release.facts.hltb?.values ?? {}
  const list = (['main', 'extra', 'complete'] as const)
    .map((key) => ({ key, hours: Number(values[key]) }))
    .filter((row) => row.hours > 0)
  const max = Math.max(...list.map((row) => row.hours), 1)
  return list.map((row) => ({ ...row, width: `${Math.max(4, (row.hours / max) * 100)}%` }))
})
</script>

<template>
  <div v-if="rows.length" class="rounded-lg border bg-card p-3" data-testid="hltb-bars">
    <p class="mb-2 font-mono text-[11px] tracking-wider text-muted-foreground uppercase">
      {{ t('works.playTime') }}
    </p>
    <div class="grid grid-cols-[auto_1fr_auto] items-center gap-x-3 gap-y-1.5 text-xs">
      <template v-for="row in rows" :key="row.key">
        <span class="text-muted-foreground">{{ t(`works.hltb.${row.key}`) }}</span>
        <span class="h-1.5 rounded-full bg-muted">
          <span class="block h-full rounded-full bg-primary" :style="{ width: row.width }" />
        </span>
        <span class="tabular text-right font-mono"
          >{{ n(row.hours, { maximumFractionDigits: 1 }) }} h</span
        >
      </template>
    </div>
  </div>
</template>
