<script setup lang="ts">
import {
  ArrowRightLeft,
  BookmarkCheck,
  CloudDownload,
  Disc3,
  Gamepad2,
  HandCoins,
  Image as ImageIcon,
  Merge,
  Pencil,
  Plus,
  RotateCcw,
  Trash2,
} from '@lucide/vue'
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import DetailPage from '@/components/app/DetailPage.vue'
import PlatformBadge from '@/components/app/PlatformBadge.vue'
import UnreviewedBadge from '@/components/app/UnreviewedBadge.vue'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { DropdownMenuItem, DropdownMenuSeparator } from '@/components/ui/dropdown-menu'
import type { Item } from '@/api/types'
import { useFactsOnOpen } from '@/features/integrations/composables/useFacts'
import { canEdit, useLibrary } from '@/features/library/composables/useLibraries'
import { useProviders } from '@/features/library/composables/useReference'
import AddToListMenu from '@/features/lists/components/AddToListMenu.vue'
import WatchButton from '@/features/watchlist/components/WatchButton.vue'
import DeleteCopyDialog from '@/features/works/components/DeleteCopyDialog.vue'
import { copiesPerRelease, useCopyActions } from '@/features/works/composables/useCopyActions'
import { useWorkTrackings } from '@/features/works/composables/useWork'
import { useAuthStore } from '@/stores/auth'
import CopyFacts from '../components/CopyFacts.vue'
import CopyShelf from '../components/CopyShelf.vue'
import GameFacts from '../components/GameFacts.vue'
import GameHead from '../components/GameHead.vue'
import GameSection from '../components/GameSection.vue'
import RelatedLinks from '../components/RelatedLinks.vue'
import ReleaseFacts from '../components/ReleaseFacts.vue'
import ReleaseTimeline from '../components/ReleaseTimeline.vue'
import SeriesSection from '../components/SeriesSection.vue'
import { useGamePage } from '../composables/useGamePage'
import { useSections, type Section } from '../composables/useSections'

/** The game page – one page for a game, its releases and your copies of it, focused by its
 * address on a copy (/items/<id>), a release (/releases/<id>) or the game (/works/<id>).
 * Every focus shows the same sections in the same order, each folding in and out
 * (remembered per focus); the focus decides the cover, the kicker, what's in front and
 * which sections there are (no "this copy" without a copy). See
 * docs/concept-detail-page.md. */
const { t, n } = useI18n()
const router = useRouter()
const auth = useAuthStore()
const {
  focus,
  libraryId,
  item,
  release,
  work,
  workId,
  releases,
  copies,
  copiesPending,
  loaded,
  isError,
} = useGamePage()
const sections = useSections(focus)
const open = (section: Section) => ({
  open: sections.isOpen(section),
  'onUpdate:open': (value: boolean) => sections.setOpen(section, value),
})

const library = useLibrary(libraryId)
const editable = computed(() => canEdit(library.data.value?.role))
const { addCopy, giveBack } = useCopyActions(libraryId)
const providers = useProviders()
const enabled = (kind: string) =>
  (providers.data.value ?? []).filter((p) => p.kind === kind && p.enabled)
const coverSources = computed(() => enabled('covers').length > 0)
const metadataSource = computed(() => enabled('metadata')[0])
/** Looking for a cover: for your copy (editors), for the release (admins). */
const findCover = computed(
  () => coverSources.value && ((!!item.value && editable.value) || auth.isAdmin),
)
// Play times and scores are shown from the cache; opening the game refreshes stale ones.
const factSources = useFactsOnOpen(workId)

const title = computed(() =>
  focus.value === 'item'
    ? (item.value?.title ?? '')
    : focus.value === 'release'
      ? (release.value?.title ?? '')
      : (work.data.value?.title ?? ''),
)
/** The copy's cover, the release's, or for the game its own – else a copy's (what's on
 * your shelf) or the release's. */
const cover = computed(() => {
  if (focus.value === 'item')
    return { src: item.value?.cover_url ?? null, aspect: item.value?.cover_aspect ?? null }
  if (focus.value === 'work' && work.data.value?.cover_url)
    return { src: work.data.value.cover_url, aspect: work.data.value.cover_aspect }
  const copy = focus.value === 'work' && copies.value.find((c) => c.cover_url)
  if (copy) return { src: copy.cover_url, aspect: copy.cover_aspect }
  return { src: release.value?.cover_url ?? null, aspect: release.value?.cover_aspect ?? null }
})

const owned = copiesPerRelease(copies)
/** Your copies, those of the release the page is about first. */
const shelf = computed(() => {
  const id = release.value?.id
  if (focus.value === 'work' || !id) return copies.value
  return [
    ...copies.value.filter((c) => c.release.id === id),
    ...copies.value.filter((c) => c.release.id !== id),
  ]
})
/** What your copies are worth together (editors only see values). */
const totalValue = computed(() =>
  copies.value.reduce((sum, copy) => sum + (Number(copy.current_value) || 0), 0),
)
const trackings = useWorkTrackings(workId)
const othersTracking = computed(() => (trackings.data.value ?? []).filter((tr) => !tr.is_mine))
const platforms = computed(() => {
  const seen = new Map<string, (typeof releases.value)[number]['platform']>()
  for (const r of releases.value) seen.set(r.platform.id, r.platform)
  return [...seen.values()]
})
const releasePending = computed(
  () => release.value?.review_status === 'pending' || !!release.value?.pending_barcodes.length,
)
const hasLinks = computed(
  () => focus.value !== 'work' || Object.values(release.value?.facts ?? {}).some((f) => f.url),
)

const removing = ref<Item | null>(null)
function deleted(copy: Item) {
  void router.push({ name: 'work', params: { workId: copy.release.work_id } })
}
</script>

<template>
  <DetailPage :library-id="libraryId" :loaded="loaded" :error="isError">
    <template v-if="release">
      <GameHead
        :title="title"
        :release="release"
        :focus="focus"
        :cover="cover"
        :cover-pending="focus === 'work' && !work.data.value?.cover_url && copiesPending"
        :menu-label="t(`game.actions.${focus}`)"
        :loan="item?.active_loan"
      >
        <!-- A copy is simply yours; the others say what they are and where they belong. -->
        <template v-if="focus !== 'item'" #kicker>
          <template v-if="focus === 'release'">
            <Disc3 class="size-3.5" />
            {{ t('game.releaseOf') }}
            <RouterLink
              :to="{ name: 'work', params: { workId } }"
              class="tracking-normal normal-case text-primary hover:underline"
              data-testid="kicker-game"
              >{{ release.work_title }}</RouterLink
            >
          </template>
          <template v-else>
            <Gamepad2 class="size-3.5" />
            {{ t('game.kicker', { n: releases.length }, releases.length) }}
            <PlatformBadge v-for="p in platforms" :key="p.id" :platform="p" class="ml-1" />
          </template>
        </template>

        <template #menu>
          <AddToListMenu v-if="focus !== 'work'" sub :release-id="release.id" :item-id="item?.id" />
          <template v-if="item && editable">
            <DropdownMenuItem
              v-if="item.active_loan"
              data-testid="return-copy"
              @select="giveBack(item.active_loan.id)"
            >
              <RotateCcw class="size-4" /> {{ t('items.giveBack') }}
            </DropdownMenuItem>
          </template>
          <template v-if="focus !== 'work' && (release.can_edit || findCover || auth.isAdmin)">
            <DropdownMenuSeparator />
            <DropdownMenuItem v-if="release.can_edit" as-child>
              <RouterLink
                data-testid="edit-release"
                :to="{
                  name: 'release-edit',
                  params: { releaseId: release.id },
                  query: { back: $route.fullPath },
                }"
              >
                <Pencil class="size-4" /> {{ t('items.page.editRelease') }}
              </RouterLink>
            </DropdownMenuItem>
            <DropdownMenuItem v-if="findCover" as-child>
              <RouterLink
                data-testid="find-cover"
                :to="{
                  name: 'cover-search',
                  params: { releaseId: release.id },
                  query: { back: $route.fullPath, ...(item ? { item: item.id } : {}) },
                }"
              >
                <ImageIcon class="size-4" /> {{ t('integrations.covers.search') }}
              </RouterLink>
            </DropdownMenuItem>
            <DropdownMenuItem v-if="auth.isAdmin" as-child>
              <RouterLink
                data-testid="move-release"
                :to="{
                  name: 'release-move',
                  params: { releaseId: release.id },
                  query: { back: $route.fullPath },
                }"
              >
                <ArrowRightLeft class="size-4" /> {{ t('works.moveRelease') }} …
              </RouterLink>
            </DropdownMenuItem>
          </template>
          <template v-if="work.data.value?.can_edit || auth.isAdmin">
            <DropdownMenuSeparator />
            <DropdownMenuItem v-if="work.data.value?.can_edit" as-child>
              <RouterLink
                data-testid="edit-work"
                :to="{ name: 'work-edit', params: { workId }, query: { back: $route.fullPath } }"
              >
                <Pencil class="size-4" /> {{ t('items.page.editGame') }}
              </RouterLink>
            </DropdownMenuItem>
            <DropdownMenuItem v-if="auth.isAdmin" as-child>
              <RouterLink
                data-testid="merge-work"
                :to="{ name: 'work-merge', params: { workId }, query: { back: $route.fullPath } }"
              >
                <Merge class="size-4" /> {{ t('works.mergeMenu') }}
              </RouterLink>
            </DropdownMenuItem>
            <DropdownMenuItem v-if="auth.isAdmin && metadataSource" as-child>
              <RouterLink
                data-testid="match-metadata"
                :to="{
                  name: 'metadata-match',
                  params: { workId, source: metadataSource.name },
                  query: { back: $route.fullPath },
                }"
              >
                <CloudDownload class="size-4" /> {{ t('works.matchData') }}
              </RouterLink>
            </DropdownMenuItem>
          </template>
          <template v-if="item && editable">
            <DropdownMenuSeparator />
            <DropdownMenuItem
              variant="destructive"
              data-testid="delete-copy"
              @select="removing = item"
            >
              <Trash2 class="size-4" /> {{ t('works.deleteCopy') }}
            </DropdownMenuItem>
          </template>
        </template>

        <GameSection
          v-if="item"
          v-bind="open('copy')"
          :title="t('items.page.thisCopy')"
          testid="copy-section"
        >
          <template v-if="item.overrides.length" #badges>
            <Badge
              variant="outline"
              class="font-normal"
              :title="
                t('items.overrides.current', {
                  fields: item.overrides.map((f) => t(`items.overrides.fields.${f}`)).join(', '),
                })
              "
              data-testid="own-values"
            >
              {{ t('items.overrides.badge') }}
            </Badge>
          </template>
          <template v-if="editable" #actions>
            <Button as-child size="sm" variant="outline" data-testid="edit-copy">
              <RouterLink :to="{ name: 'item-edit', params: { itemId: item.id } }">
                <Pencil class="size-4" /> {{ t('items.editCopy') }}
              </RouterLink>
            </Button>
            <Button
              v-if="!item.active_loan"
              as-child
              size="sm"
              variant="ghost"
              data-testid="lend-copy"
            >
              <RouterLink :to="{ name: 'item-lend', params: { itemId: item.id } }">
                <HandCoins class="size-4" /> {{ t('items.lend') }}
              </RouterLink>
            </Button>
          </template>
          <CopyFacts :item="item" />
        </GameSection>

        <GameSection
          v-bind="open('collection')"
          :title="t('game.inCollection')"
          :count="copiesPending ? undefined : copies.length"
          testid="collection-section"
        >
          <template v-if="totalValue" #badges>
            <span
              class="font-mono text-xs font-normal text-muted-foreground tabular"
              data-testid="collection-value"
            >
              {{ t('game.worth', { value: n(totalValue, 'currency') }) }}
            </span>
          </template>
          <template v-if="focus !== 'work'" #actions>
            <Button
              v-if="editable"
              size="sm"
              variant="outline"
              data-testid="add-copy"
              @click="addCopy(release.id)"
            >
              <Plus class="size-4" /> {{ t('game.addCopy') }}
            </Button>
            <WatchButton
              v-if="focus === 'release' && !copiesPending && !owned[release.id]"
              :release-id="release.id"
            />
          </template>
          <CopyShelf v-if="copies.length" :copies="shelf" :current="item?.id" />
          <p
            v-else-if="!copiesPending"
            class="rounded-lg border border-dashed p-4 text-sm text-muted-foreground"
            data-testid="no-copies"
          >
            {{ focus === 'work' ? t('game.noCopiesPick') : t('game.noCopies') }}
          </p>
          <ul
            v-if="othersTracking.length"
            class="mt-4 space-y-1 text-sm"
            data-testid="others-tracking"
          >
            <li v-for="entry in othersTracking" :key="entry.id" class="flex items-center gap-2">
              <BookmarkCheck class="size-4 text-primary" />
              {{
                t('works.trackedBy', {
                  user: entry.user,
                  status: t(`choices.tracking.${entry.status}`),
                })
              }}
              <PlatformBadge :platform="entry.release.platform" />
            </li>
          </ul>
        </GameSection>

        <GameSection
          v-if="focus !== 'work'"
          v-bind="open('release')"
          :title="t('game.thisRelease')"
          testid="release-section"
        >
          <template v-if="releasePending" #badges><UnreviewedBadge /></template>
          <ReleaseFacts :release="release" :item="item" />
        </GameSection>

        <GameSection v-bind="open('game')" :title="t('game.theGame')" testid="game-section">
          <template v-if="work.data.value?.review_status === 'pending'" #badges>
            <UnreviewedBadge />
          </template>
          <GameFacts :release="release" :releases="releases" :sources="factSources" />
        </GameSection>

        <GameSection
          v-if="releases.length"
          v-bind="open('releases')"
          :title="t('game.allReleases')"
          :count="releases.length"
          testid="releases-section"
        >
          <ReleaseTimeline
            :releases="releases"
            :owned="owned"
            :current="focus === 'work' ? undefined : release.id"
          />
        </GameSection>

        <SeriesSection
          v-for="series in release.series.slice(0, 1)"
          :key="series.id"
          v-bind="open('series')"
          :series="series"
          :work-id="workId"
        />

        <GameSection
          v-if="hasLinks"
          v-bind="open('links')"
          :title="t('game.links')"
          testid="links-section"
        >
          <RelatedLinks :release="release" :focus="focus" />
        </GameSection>
      </GameHead>
    </template>
  </DetailPage>
  <DeleteCopyDialog v-model:item="removing" :library-id="libraryId" @deleted="deleted" />
</template>
