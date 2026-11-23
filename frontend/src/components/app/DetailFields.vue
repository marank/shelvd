<script setup lang="ts">
import type { RouteLocationRaw } from 'vue-router'
import { isMono, useFieldLabel, type ItemFieldKey } from '@/lib/itemFields'
import { cn } from '@/lib/utils'

/** Label/value pairs of one level's fields (only those with a value). "grid" spreads
 * them over columns (game, release blocks), "rows" puts labels beside values (copies, the
 * explorer's column), "stack" lists them one below the other (a column of `FieldColumns`).
 * Terms link to their pages in all. */
defineProps<{
  entries: {
    key: ItemFieldKey
    parts: string[]
    links?: { id: string; name: string; to: RouteLocationRaw }[] | null
  }[]
  variant?: 'grid' | 'rows' | 'stack'
}>()
const label = useFieldLabel()
</script>

<template>
  <dl
    v-if="variant === 'rows'"
    class="grid grid-cols-[minmax(6rem,auto)_1fr] gap-x-3 gap-y-0.5 text-sm"
    data-testid="detail-fields"
  >
    <template v-for="entry in entries" :key="entry.key">
      <dt class="font-mono text-[11px] leading-5 tracking-wider text-muted-foreground uppercase">
        {{ label(entry.key) }}
      </dt>
      <dd
        :class="
          cn('min-w-0 break-words', isMono(entry.key) && 'tabular font-mono text-xs leading-5')
        "
        :data-field="entry.key"
      >
        <template v-if="entry.links">
          <template v-for="(link, i) in entry.links" :key="link.id">
            <span v-if="i > 0" class="text-muted-foreground">, </span>
            <RouterLink :to="link.to" class="text-primary hover:underline">{{
              link.name
            }}</RouterLink>
          </template>
        </template>
        <template v-else>{{ entry.parts.join(', ') }}</template>
      </dd>
    </template>
  </dl>
  <dl
    v-else
    :class="variant === 'stack' ? 'space-y-3' : 'grid grid-cols-2 gap-x-4 gap-y-3 @2xl:grid-cols-4'"
    data-testid="detail-fields"
  >
    <div v-for="entry in entries" :key="entry.key" class="min-w-0">
      <dt class="font-mono text-[11px] tracking-wider text-muted-foreground uppercase">
        {{ label(entry.key) }}
      </dt>
      <dd
        :class="
          cn('mt-0.5 text-sm font-medium break-words', isMono(entry.key) && 'tabular font-mono')
        "
        :data-field="entry.key"
      >
        <template v-if="entry.links">
          <template v-for="(link, i) in entry.links" :key="link.id">
            <span v-if="i > 0" class="text-muted-foreground">, </span>
            <RouterLink :to="link.to" class="text-primary hover:underline">{{
              link.name
            }}</RouterLink>
          </template>
        </template>
        <template v-else>{{ entry.parts.join(', ') }}</template>
      </dd>
    </div>
  </dl>
</template>
