<script setup lang="ts">
import { ArrowUpRight } from '@lucide/vue'
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import type { RouteLocationRaw } from 'vue-router'
import { Button } from '@/components/ui/button'
import { LEVELS, type FieldLevel } from '@/lib/itemFields'

/** Icon button to a level's own page ("Open copy"): the level's icon plus an arrow, the
 * same wherever a game, release or copy can be opened. */
const props = defineProps<{ level: FieldLevel; to: RouteLocationRaw }>()
const { t } = useI18n()
const icon = computed(() => LEVELS.find((l) => l.key === props.level)!.icon)
const label = computed(() => t(`levels.open.${props.level}`))
</script>

<template>
  <Button
    as-child
    variant="ghost"
    size="sm"
    class="h-7 gap-0.5 px-1.5 text-muted-foreground hover:text-foreground"
    :aria-label="label"
    :title="label"
  >
    <RouterLink :to="to" :data-testid="`open-${level}`">
      <component :is="icon" class="size-3.5" />
      <ArrowUpRight class="size-3.5" />
    </RouterLink>
  </Button>
</template>
