<script setup lang="ts">
// "Mehr aus der Reihe …": the other games of one of the game's series, oldest first, the
// heading linking to the series' page. Nothing when the series has no other game.
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import TermWorkCard from '@/features/terms/components/TermWorkCard.vue'
import { useTerm } from '@/features/terms/composables/useTermPages'
import { termPage } from '@/lib/terms'
import GameSection from './GameSection.vue'

const props = defineProps<{ series: { id: string; name: string }; workId: string }>()
const open = defineModel<boolean>('open', { required: true })
const { t } = useI18n()
const term = useTerm('series', () => props.series.id)
const LIMIT = 12
/** Oldest first; games without a year at the end. */
const others = computed(() =>
  (term.data.value?.works ?? [])
    .filter((w) => w.id !== props.workId)
    .sort((a, b) => (a.year ?? 9999) - (b.year ?? 9999)),
)
</script>

<template>
  <GameSection
    v-if="others.length"
    v-model:open="open"
    :title="t('works.moreFromSeries', { series: series.name })"
    :count="others.length"
    testid="series-section"
  >
    <template #actions>
      <RouterLink
        :to="termPage('series', series.id)"
        class="text-xs text-primary hover:underline"
        data-testid="series-link"
      >
        {{ t('game.toSeries') }}
      </RouterLink>
    </template>
    <div class="grid grid-cols-[repeat(auto-fill,minmax(6.5rem,1fr))] items-end gap-x-1 gap-y-3">
      <TermWorkCard v-for="work in others.slice(0, LIMIT)" :key="work.id" :work="work" />
    </div>
  </GameSection>
</template>
