<script setup lang="ts">
// Terms of one kind the game belongs to when there are several (franchises of a crossover
// like "LEGO Marvel Super Heroes 2"): a labelled list like the languages, each linked to its
// page; long lists show a few until opened.
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { termPage, type TermKind, type TermRef } from '@/lib/terms'

const props = defineProps<{ kind: TermKind; label: string; terms: TermRef[] }>()
const { t } = useI18n()
const SHOWN = 6
const all = ref(false)
const visible = computed(() => (all.value ? props.terms : props.terms.slice(0, SHOWN)))
</script>

<template>
  <div v-if="terms.length" :data-testid="`term-list-${kind}`">
    <p class="mb-2 font-mono text-[11px] tracking-wider text-muted-foreground uppercase">
      {{ label }}
    </p>
    <ul class="divide-y text-sm">
      <li v-for="term in visible" :key="term.id" class="py-1.5">
        <RouterLink :to="termPage(kind, term.id)" class="text-primary hover:underline">{{
          term.name
        }}</RouterLink>
      </li>
    </ul>
    <button
      v-if="terms.length > SHOWN"
      type="button"
      class="mt-1 text-xs text-primary hover:underline"
      :data-testid="`term-list-${kind}-more`"
      @click="all = !all"
    >
      {{ all ? t('game.fewer') : t('game.showAll', { n: terms.length, label }) }}
    </button>
  </div>
</template>
