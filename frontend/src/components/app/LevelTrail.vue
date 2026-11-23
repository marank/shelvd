<script setup lang="ts">
import { ChevronRight } from '@lucide/vue'
import type { RouteLocationRaw } from 'vue-router'
import { LEVELS, type FieldLevel } from '@/lib/itemFields'

/** Where a page sits: Spiel › Ausgabe › Exemplar, each with its level's icon. Every step
 * but the last links to its page. */
defineProps<{ steps: { level: FieldLevel; label: string; to?: RouteLocationRaw }[] }>()
const icon = (level: FieldLevel) => LEVELS.find((l) => l.key === level)!.icon
</script>

<template>
  <nav aria-label="Breadcrumb" data-testid="level-trail">
    <ol class="flex flex-wrap items-center gap-1 text-sm text-muted-foreground">
      <li v-for="(step, i) in steps" :key="step.level" class="flex min-w-0 items-center gap-1">
        <ChevronRight v-if="i > 0" class="size-3.5 shrink-0" />
        <component :is="icon(step.level)" class="size-3.5 shrink-0" />
        <RouterLink
          v-if="step.to && i < steps.length - 1"
          :to="step.to"
          class="truncate hover:text-foreground hover:underline"
          :data-testid="`trail-${step.level}`"
        >
          {{ step.label }}
        </RouterLink>
        <span v-else class="truncate font-medium text-foreground" aria-current="page">
          {{ step.label }}
        </span>
      </li>
    </ol>
  </nav>
</template>
