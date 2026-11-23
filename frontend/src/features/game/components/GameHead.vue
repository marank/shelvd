<script setup lang="ts">
// The game page in two columns: on the left the cover with the game's franchises, series
// and who made it below it – logo or name, linked (same width, staying in view on wide
// screens); on the right what the page is about (kicker), the title (with the release
// number beside it), what the game is about, a few figures – no tags – and then the
// page's sections (default slot). On phones everything is one column, the blocks under the
// cover last. Focused on the game, there's no release number and no publisher (that's a
// release's).
import { Separator } from '@/components/ui/separator'
import { Skeleton } from '@/components/ui/skeleton'
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import CoverImage from '@/components/app/CoverImage.vue'
import DetailHero from '@/components/app/DetailHero.vue'
import HeroStats from '@/components/app/HeroStats.vue'
import type { Item, Release } from '@/api/types'
import { useAddonFigures } from '@/addons'
import type { Focus } from '../composables/useGamePage'
import TermBlock from './TermBlock.vue'

const props = defineProps<{
  title: string
  release: Release
  focus: Focus
  cover: { src: string | null; aspect: number | null }
  /** Wait with the cover (it may still change). */
  coverPending?: boolean
  menuLabel: string
  /** The copy's loan while it's lent (a figure of its own). */
  loan?: Item['active_loan']
}>()
const { t } = useI18n()

const expanded = ref(false)
const summary = computed(() => props.release.summary.trim())
const longSummary = computed(() => summary.value.length > 320)

/** The game's series (all of them: "The Legend of Zelda" and "… Ocarina of Time") and who
 * made it – developer and publisher always apart, even when it's one company. Under the
 * cover, on phones at the end. */
const blocks = computed(() => {
  const release = props.release
  const developer = release.developers[0]
  return [
    // Several franchises (crossovers) are a list in the game's section, not blocks here.
    ...(release.franchises.length === 1 ? release.franchises : []).map((f) => ({
      key: `franchise-${f.id}`,
      kind: 'franchises' as const,
      id: f.id,
      name: f.name,
      label: t('itemFields.game.franchises'),
    })),
    ...release.series.map((s) => ({
      key: `series-${s.id}`,
      kind: 'series' as const,
      id: s.id,
      name: s.name,
      label: t('itemFields.game.series'),
    })),
    ...(developer
      ? [
          {
            key: 'developer',
            kind: 'companies' as const,
            id: developer.id,
            name: developer.name,
            label: t('itemFields.game.developers'),
          },
        ]
      : []),
    ...(release.publisher && props.focus !== 'work'
      ? [
          {
            key: 'publisher',
            kind: 'companies' as const,
            id: release.publisher.id,
            name: release.publisher.name,
            label: t('itemObjects.publisher'),
          },
        ]
      : []),
  ]
})

// Add-ons' figures (e.g. own play time): the whole game, or this platform.
const addonFigures = useAddonFigures(() => ({
  workId: props.release.work_id,
  platformId: props.focus === 'work' ? null : props.release.platform.id,
}))
const figures = computed(() => [
  ...(props.loan
    ? [
        {
          key: 'loan',
          label: t('items.lent'),
          // Viewers learn that it's lent, not to whom.
          value: props.loan.borrower?.name ?? t('items.page.yes'),
          accent: true,
        },
      ]
    : []),
  ...addonFigures.value,
])
</script>

<template>
  <DetailHero
    class="@lg:gap-8"
    testid="game"
    :title="title"
    :suffix="release.release_number && focus !== 'work' ? `#${release.release_number}` : undefined"
    :manufacturer="release.platform.manufacturer"
    :menu-label="menuLabel"
  >
    <template #visual>
      <div
        class="w-64 max-w-full shrink-0 space-y-4 self-center @lg:sticky @lg:top-4 @lg:self-start @3xl:w-72"
        data-testid="cover-column"
      >
        <Skeleton v-if="coverPending" class="aspect-[5/7] w-full" data-testid="cover-pending" />
        <CoverImage
          v-else
          :src="cover.src"
          :aspect="cover.aspect"
          :title="title"
          :manufacturer="release.platform.manufacturer"
          class="w-full shadow-md"
        />
        <div v-if="blocks.length" class="hidden space-y-4 @lg:block">
          <template v-for="block in blocks" :key="block.key">
            <Separator />
            <TermBlock v-bind="block" />
          </template>
        </div>
      </div>
    </template>
    <template v-if="$slots.kicker" #kicker><slot name="kicker" /></template>
    <template v-if="$slots.menu" #menu><slot name="menu" /></template>
    <div v-if="summary" data-testid="game-summary">
      <p
        class="text-sm leading-relaxed whitespace-pre-line text-muted-foreground"
        :class="!expanded && 'line-clamp-4'"
      >
        {{ summary }}
      </p>
      <button
        v-if="longSummary"
        type="button"
        class="mt-1 text-xs text-primary hover:underline"
        data-testid="summary-more"
        @click="expanded = !expanded"
      >
        {{ expanded ? t('items.page.less') : t('items.page.more') }}
      </button>
    </div>
    <HeroStats
      :release="release"
      :fields="['game.time_main', 'game.time_complete', 'game.critic_score']"
      :extra="figures"
    />
    <div v-if="$slots.default" class="space-y-10 pt-4">
      <slot />
    </div>
    <!-- On phones its series and who made it come last. -->
    <div v-if="blocks.length" class="space-y-4 pt-4 @lg:hidden" data-testid="about-end">
      <template v-for="block in blocks" :key="block.key">
        <Separator />
        <TermBlock v-bind="block" />
      </template>
    </div>
  </DetailHero>
</template>
