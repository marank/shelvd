<script setup lang="ts">
// "Das Spiel": what kind of game it is and how it's played – first release, genres,
// modes, perspective –, its franchises when there are several, its languages, how long it
// takes (HowLongToBeat, then what add-ons add, e.g. own play time) and where these facts come from. One franchise,
// its series and who made it are beside the cover.
import { computed } from 'vue'
import { collect } from '@/addons'
import { useI18n } from 'vue-i18n'
import FieldColumns from '@/components/app/FieldColumns.vue'
import type { Release } from '@/api/types'
import FactSources from '@/features/integrations/components/FactSources.vue'
import HltbBars from '@/features/works/components/HltbBars.vue'
import { useFieldValue, type ItemFieldKey } from '@/lib/itemFields'
import LanguageTable from './LanguageTable.vue'
import TermList from './TermList.vue'
import { firstText } from '@/lib/utils'

const props = defineProps<{
  release: Release
  /** Every release of the game: the first one's platform goes beside its date. */
  releases: Release[]
  /** Show where the facts come from (an active facts source). */
  sources: boolean
}>()
const GROUPS: ItemFieldKey[][] = [
  ['game.first_release', 'game.genres'],
  ['game.modes', 'game.perspectives'],
]
const { t } = useI18n()
/** Add-ons' blocks after HowLongToBeat, each given the release. */
const addonFacts = collect('gameFacts').flat()
const value = useFieldValue()
/** The first release with the platform it came out on: "12.12.1998 (N64)". */
const texts = computed((): Partial<Record<ItemFieldKey, string>> => {
  const first = props.release.first_release_date
  if (!first) return {}
  const earliest = props.releases.find((r) => r.release_date === first)
  const date = value.parts('game.first_release', props.release).join('')
  const platform = firstText(earliest?.platform.short_name, earliest?.platform.name)
  return { 'game.first_release': platform ? `${date} (${platform})` : date }
})
</script>

<template>
  <div class="space-y-6">
    <div class="grid gap-6 @3xl:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)]">
      <FieldColumns :groups="GROUPS" :release="release" :texts="texts" />
      <div class="grid content-start gap-3">
        <HltbBars :release="release" />
        <component :is="fact" v-for="(fact, i) in addonFacts" :key="i" :release="release" />
        <FactSources v-if="sources" :work-id="release.work_id" :facts="release.facts ?? {}" />
      </div>
    </div>
    <!-- Franchises and languages side by side (both lists that open); the languages alone
         under the fields, as wide as they are. -->
    <div
      class="grid gap-6"
      :class="
        release.franchises.length > 1
          ? '@3xl:grid-cols-[minmax(0,2fr)_minmax(0,3fr)]'
          : '@3xl:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)]'
      "
      data-testid="game-lists"
    >
      <TermList
        v-if="release.franchises.length > 1"
        kind="franchises"
        :label="t('nav.franchises')"
        :terms="release.franchises"
      />
      <LanguageTable :languages="release.languages ?? {}" />
    </div>
  </div>
</template>
