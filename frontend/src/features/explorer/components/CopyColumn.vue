<script setup lang="ts">
import { ArrowRight } from '@lucide/vue'
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import LevelCard from '@/components/app/LevelCard.vue'
import LevelHeading from '@/components/app/LevelHeading.vue'
import RichText from '@/components/app/RichText.vue'
import type { Item } from '@/api/types'
import { useFactsOnOpen } from '@/features/integrations/composables/useFacts'
import CopyHero from '@/features/items/components/CopyHero.vue'
import { canEdit, useLibrary } from '@/features/library/composables/useLibraries'
import DeleteCopyDialog from '@/features/works/components/DeleteCopyDialog.vue'
import { releaseLabel } from '@/features/works/composables/labels'
import { useWork, useWorkItems } from '@/features/works/composables/useWork'
import { termPage } from '@/lib/terms'
import {
  DEFAULT_FIELDS,
  fieldLevel,
  useFieldValue,
  type FieldLevel,
  type ItemFieldKey,
} from '@/lib/itemFields'
import { cn } from '@/lib/utils'

/** The explorer's column for the clicked copy: the copy first (cover, actions, the loan
 * while it's lent, its own card), the library's copies of the game, then release and game
 * as label/value rows – the view's detail fields, plus who made it and what it is. The
 * releases are one link away (the game's page). */
const props = defineProps<{
  libraryId: string
  item: Item
  /** The view's detail-column fields (default: DEFAULT_FIELDS.detail). */
  fields?: ItemFieldKey[]
}>()
/** The copy was deleted: the column has nothing left to show. */
const emit = defineEmits<{ close: [] }>()
const { t } = useI18n()
const value = useFieldValue()
const library = useLibrary(() => props.libraryId)
const editable = computed(() => canEdit(library.data.value?.role))
const workId = computed(() => props.item.release.work_id)
const work = useWork(workId)
const items = useWorkItems(() => props.libraryId, workId)
const copies = computed(() => items.data.value?.items ?? [])

// Play times, scores …: shown from the cache; opening a copy refreshes its game's stale
// ones (like the game's page).
useFactsOnOpen(workId)

const keysOf = (level: FieldLevel) =>
  (props.fields ?? DEFAULT_FIELDS.detail).filter((k) => fieldLevel(k) === level)
/** Where it stands, how complete, what it's worth and cost, since when – then the view's
 * own copy fields. */
const COPY_ALWAYS: ItemFieldKey[] = [
  'location.path',
  'copy.completeness',
  'copy.value',
  'copy.price',
  'copy.acquired',
]
const copyFields = computed(() => [...new Set([...COPY_ALWAYS, ...keysOf('item')])])
/** The essentials always, then the view's own fields. Platform, region and edition are in
 * the header; the year is part of the date. */
const RELEASE_ALWAYS: ItemFieldKey[] = [
  'publisher.name',
  'release.developers',
  'release.date',
  'release.age_rating',
  'release.barcodes',
]
const NOT_IN_RELEASE: ItemFieldKey[] = [
  'platform.name',
  'release.region',
  'release.edition',
  'release.year',
]
const GAME_ALWAYS: ItemFieldKey[] = [
  'game.developers',
  'game.genres',
  'game.series',
  'game.first_release',
  'game.time_main',
  'game.critic_score',
]
const releaseFields = computed(() =>
  [...new Set([...RELEASE_ALWAYS, ...keysOf('release')])].filter(
    (k) => !NOT_IN_RELEASE.includes(k),
  ),
)
const gameFields = computed(() => [...new Set([...GAME_ALWAYS, ...keysOf('work')])])
const releaseCount = computed(() => work.data.value?.releases.length ?? 0)
const series = computed(() => work.data.value?.series[0])
const removing = ref<Item | null>(null)
</script>

<template>
  <div class="@container space-y-6" data-testid="copy-column">
    <CopyHero
      :item="item"
      :library-id="libraryId"
      :editable="editable"
      compact
      @remove="removing = item"
    />

    <LevelCard
      level="item"
      :title="t('levels.item')"
      :release="item.release"
      :item="item"
      :fields="copyFields"
      compact
    />

    <section v-if="copies.length > 1" data-testid="column-copies">
      <LevelHeading
        level="item"
        :title="t('works.copiesIn', { library: library.data.value?.name ?? '' })"
        :count="copies.length"
      />
      <ul class="divide-y rounded-lg border bg-card text-sm">
        <li v-for="copy in copies" :key="copy.id">
          <RouterLink
            :to="{ query: { ...$route.query, item: copy.id } }"
            replace
            :class="
              cn(
                'flex w-full items-baseline gap-3 px-3 py-2 text-left hover:bg-accent/40',
                copy.id === item.id && 'bg-accent/30 font-medium',
              )
            "
            :aria-current="copy.id === item.id ? 'true' : undefined"
            data-testid="column-copy"
          >
            <span class="min-w-0 flex-1 truncate">{{ releaseLabel(copy.release) }}</span>
            <span class="truncate text-xs text-muted-foreground">
              {{ [copy.location?.path, value('copy.value', copy)].filter(Boolean).join(' · ') }}
            </span>
          </RouterLink>
        </li>
      </ul>
    </section>

    <LevelCard
      level="release"
      :title="t('levels.release')"
      :release="item.release"
      :to="{ name: 'release', params: { releaseId: item.release.id } }"
      :fields="releaseFields"
      compact
    />

    <LevelCard
      level="work"
      :title="t('levels.work')"
      :release="item.release"
      :item="item"
      :to="{ name: 'work', params: { workId } }"
      :fields="gameFields"
      compact
    >
      <template #before>
        <RichText
          v-if="work.data.value?.summary"
          :text="work.data.value.summary"
          class="mb-3 line-clamp-3 text-sm leading-relaxed text-muted-foreground"
          data-testid="column-summary"
        />
      </template>
    </LevelCard>

    <nav class="flex flex-wrap justify-between gap-x-4 gap-y-2 text-sm" data-testid="column-links">
      <RouterLink
        v-if="releaseCount"
        :to="{ name: 'work', params: { workId } }"
        class="inline-flex items-center gap-1 text-primary hover:underline"
        data-testid="column-releases"
      >
        {{ t('explorer.column.releases', { n: releaseCount }, releaseCount) }}
        <ArrowRight class="size-3.5" />
      </RouterLink>
      <RouterLink
        v-if="series"
        :to="termPage('series', series.id)"
        class="inline-flex items-center gap-1 text-primary hover:underline"
        data-testid="column-series"
      >
        {{ t('works.moreFromSeries', { series: series.name }) }}
        <ArrowRight class="size-3.5" />
      </RouterLink>
    </nav>

    <DeleteCopyDialog v-model:item="removing" :library-id="libraryId" @deleted="emit('close')" />
  </div>
</template>
