<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { TERM_ICONS, termPage, type TermKind } from '@/lib/terms'

/** Companies, genres and series as chips leading to their pages, each with its kind's
 * symbol (and a count, e.g. how many games share it). */
defineProps<{ terms: { kind: TermKind; id: string; name: string; count?: number }[] }>()
const { t } = useI18n()
</script>

<template>
  <ul v-if="terms.length" class="flex flex-wrap gap-1.5" data-testid="term-chips">
    <li v-for="term in terms" :key="`${term.kind}-${term.id}`">
      <RouterLink
        :to="termPage(term.kind, term.id)"
        class="inline-flex items-center gap-1.5 rounded-full border bg-card px-2.5 py-1 text-xs transition hover:border-foreground/20 hover:bg-accent/50"
        :title="t(`terms.${term.kind}.one`)"
      >
        <component :is="TERM_ICONS[term.kind]" class="size-3.5 text-muted-foreground" />
        {{ term.name }}
        <span
          v-if="term.count !== undefined"
          class="tabular font-mono text-[11px] text-muted-foreground"
          >{{ term.count }}</span
        >
      </RouterLink>
    </li>
  </ul>
</template>
