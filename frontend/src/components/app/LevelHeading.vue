<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import type { RouteLocationRaw } from 'vue-router'
import LevelLink from '@/components/app/LevelLink.vue'
import { LEVELS, type FieldLevel } from '@/lib/itemFields'

/** Section title that says what level it shows (game / release / copy) and whose data it
 * is (shared catalog or this collection) – the same icon and words everywhere. */
const props = defineProps<{
  level: FieldLevel
  title: string
  scope?: string
  count?: number
  /** The level's own page: an "open" icon button at the end. */
  to?: RouteLocationRaw
}>()
const { t } = useI18n()
const meta = computed(() => LEVELS.find((l) => l.key === props.level)!)
</script>

<template>
  <h2 class="mb-3 flex items-center gap-2 text-sm font-semibold" :data-level="level">
    <component :is="meta.icon" class="size-4 text-muted-foreground" />
    <span class="min-w-0 truncate"
      ><slot name="title">{{ title }}</slot></span
    >
    <span v-if="count !== undefined" class="tabular font-mono text-xs text-muted-foreground">
      {{ count }}
    </span>
    <span
      class="ml-auto rounded-sm border px-1.5 py-px font-mono text-[10px] font-normal tracking-wider text-muted-foreground uppercase"
      :class="meta.scope === 'library' && 'border-primary/30 text-primary'"
    >
      {{ scope ?? t(`scopes.${meta.scope}`) }}
    </span>
    <LevelLink v-if="to" :level="level" :to="to" class="-my-1" />
  </h2>
</template>
