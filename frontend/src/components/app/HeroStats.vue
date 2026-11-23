<script setup lang="ts">
import { computed } from 'vue'
import type { Item, Release } from '@/api/types'
import { isMono, useFieldLabel, useFieldValue, type ItemFieldKey } from '@/lib/itemFields'
import { cn } from '@/lib/utils'

/** The figures at the top of a detail page (game, release, copy, company …): small
 * labels over large values. `extra` are figures of their own (counts …); `fields` are
 * item fields, shown only when they have a value. `accent` marks the most important. */
const props = defineProps<{
  extra?: {
    key: string
    label: string
    value: string | number
    accent?: boolean
    /** Up (green) or down (red), e.g. a copy's value against its price. */
    tone?: 'up' | 'down'
  }[]
  fields?: ItemFieldKey[]
  release?: Release
  item?: Item
  accent?: ItemFieldKey
}>()
const label = useFieldLabel()
const value = useFieldValue()
const stats = computed(() => [
  ...(props.extra ?? []).map((s) => ({ ...s, value: String(s.value), mono: true })),
  ...(props.release ? (props.fields ?? []) : [])
    .map((key) => ({
      key,
      label: label(key),
      value: value.parts(key, props.release!, props.item).join(', '),
      accent: key === props.accent,
      tone: undefined,
      mono: isMono(key),
    }))
    .filter((s) => s.value),
])
</script>

<template>
  <dl v-if="stats.length" class="flex flex-wrap gap-x-6 gap-y-3" data-testid="hero-stats">
    <div v-for="s in stats" :key="s.key" class="min-w-0" :data-stat="s.key">
      <dt class="font-mono text-[11px] tracking-wider text-muted-foreground uppercase">
        {{ s.label }}
      </dt>
      <dd
        :class="
          cn(
            'truncate text-lg font-semibold',
            s.mono && 'tabular font-mono',
            s.accent && 'text-primary',
            s.tone === 'up' && 'text-success',
            s.tone === 'down' && 'text-destructive',
          )
        "
      >
        {{ s.value }}
      </dd>
    </div>
  </dl>
</template>
