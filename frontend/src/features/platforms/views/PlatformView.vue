<script setup lang="ts">
import { ArrowLeft, ArrowRight, BookOpen, Building2, ImagePlus, Pencil, Plus } from '@lucide/vue'
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import BackButton from '@/components/app/BackButton.vue'
import DetailHero from '@/components/app/DetailHero.vue'
import HeroStats from '@/components/app/HeroStats.vue'
import PlatformBadge from '@/components/app/PlatformBadge.vue'
import TermChips from '@/components/app/TermChips.vue'
import ToneBox from '@/components/app/ToneBox.vue'
import { DropdownMenuItem } from '@/components/ui/dropdown-menu'
import { Skeleton } from '@/components/ui/skeleton'
import { Switch } from '@/components/ui/switch'
import { useCurrentLibrary } from '@/features/library/composables/useCurrentLibrary'
import { useLibrary } from '@/features/library/composables/useLibraries'
import { useOwned } from '@/features/library/composables/useOwned'
import TermVisual from '@/features/terms/components/TermVisual.vue'
import TermWorkCard from '@/features/terms/components/TermWorkCard.vue'
import { useDescribers, type TermWork } from '@/features/terms/composables/useTermPages'
import { languageName } from '@/lib/displayNames'
import { KIND_ICONS, describeRoute, imageRoute, platformPage, termPage } from '@/lib/terms'
import { cn } from '@/lib/utils'
import { useAuthStore } from '@/stores/auth'
import { usePlatform, usePlatformGames } from '../composables/usePlatforms'

/** A platform's page, like a company's: photo of the device (else the logo; with both the
 * logo sits above the figures), description, facts (generation, years,
 * manufacturer, predecessors and successors), what its games have in common and the
 * games themselves – from the whole catalog, the current library's marked. */
const { t, locale } = useI18n()
const props = defineProps<{ platformId: string }>()
const auth = useAuthStore()
const platformId = computed(() => props.platformId)
const platform = usePlatform(platformId)
const games = usePlatformGames(platformId)
const { id: libraryId } = useCurrentLibrary()
const library = useLibrary(libraryId)
const owned = useOwned(libraryId)
const copies = (work: TermWork) => owned.data.value?.works.get(work.id) ?? 0

const sort = ref<'year' | 'title'>('year')
const onlyOwned = ref(false)
watch(platformId, () => (onlyOwned.value = false))

const allWorks = computed(() => games.data.value?.works ?? [])
const ownedCount = computed(() => allWorks.value.filter((w) => copies(w) > 0).length)
const collator = new Intl.Collator(undefined, { sensitivity: 'base', numeric: true })
const shown = computed(() => {
  const list = onlyOwned.value ? allWorks.value.filter((w) => copies(w) > 0) : [...allWorks.value]
  return sort.value === 'title'
    ? list.sort((a, b) => collator.compare(a.title, b.title))
    : list.sort((a, b) => (a.year ?? 9999) - (b.year ?? 9999))
})

/** "2017", "2017–2025" or "–2025": when it was made. */
const lifetime = computed(() => {
  const p = platform.data.value
  if (!p?.release_year && !p?.discontinued) return ''
  return p.discontinued ? `${p.release_year ?? ''}–${p.discontinued}` : String(p.release_year)
})
const stats = computed(() => {
  const p = platform.data.value
  return [
    ...(p?.generation
      ? [{ key: 'generation', label: t('platforms.page.generation'), value: p.generation }]
      : []),
    ...(lifetime.value
      ? [
          {
            key: 'years',
            label: p?.discontinued ? t('platforms.page.built') : t('platforms.page.released'),
            value: lifetime.value,
          },
        ]
      : []),
    { key: 'games', label: t('terms.games'), value: allWorks.value.length },
    ...(libraryId.value && allWorks.value.length
      ? [
          {
            key: 'owned',
            label: t('terms.inLibrary', { library: library.data.value?.name ?? '' }),
            value: ownedCount.value,
            accent: true,
          },
        ]
      : []),
  ]
})

const describers = useDescribers('platforms')
const otherLanguage = computed(() => {
  const code = platform.data.value?.description_language
  return code && code !== locale.value ? languageName(code, locale.value) : ''
})
const expanded = ref(false)
const longDescription = computed(() => {
  const text = platform.data.value?.description ?? ''
  return text.length > 400 || text.split('\n').length > 5
})
const edit = computed(() => ({
  name: 'platform-edit',
  params: { platformId: platformId.value },
  query: { back: `/platforms/${platformId.value}` },
}))
</script>

<template>
  <div class="flex-1 overflow-y-auto" data-testid="PlatformView">
    <div class="@container mx-auto max-w-5xl space-y-8 px-4 py-4 md:px-6 md:py-6">
      <BackButton :fallback="{ name: 'platforms' }" />

      <p v-if="platform.isError.value" class="py-16 text-center text-muted-foreground">
        {{ t('errors.notFound') }}
      </p>
      <template v-else-if="platform.data.value">
        <DetailHero
          :title="platform.data.value.name"
          :menu-label="t('platforms.page.actions')"
          testid="platform"
        >
          <template #visual>
            <TermVisual
              kind="platforms"
              :name="platform.data.value.name"
              :image-url="platform.data.value.photo_url ?? platform.data.value.image_url"
              :photo="!!platform.data.value.photo_url"
              :tone="
                platform.data.value.photo_url
                  ? platform.data.value.photo_tone
                  : platform.data.value.image_tone
              "
              :works="allWorks"
            />
          </template>
          <template #kicker>
            <RouterLink
              :to="{ name: 'platforms' }"
              class="inline-flex items-center gap-1.5 hover:text-foreground"
            >
              <component :is="KIND_ICONS.platforms" class="size-3.5" />
              {{ t('platforms.page.kicker') }}
            </RouterLink>
            <PlatformBadge :platform="platform.data.value" />
          </template>
          <template v-if="auth.isAdmin" #menu>
            <DropdownMenuItem as-child>
              <RouterLink :to="edit" data-testid="platform-edit">
                <Pencil class="size-4" /> {{ t('actions.edit') }}
              </RouterLink>
            </DropdownMenuItem>
            <DropdownMenuItem v-for="d in describers" :key="d.name" as-child>
              <RouterLink
                :to="describeRoute('platforms', platformId, d.name)"
                :data-testid="`platform-describe-${d.name}`"
              >
                <BookOpen class="size-4" />
                {{ t('terms.describe.menu', { source: d.label }) }}
              </RouterLink>
            </DropdownMenuItem>
            <DropdownMenuItem v-if="describers.length" as-child>
              <RouterLink
                :to="imageRoute('platforms', platformId)"
                data-testid="platform-choose-image"
              >
                <ImagePlus class="size-4" /> {{ t('terms.images.menu') }}
              </RouterLink>
            </DropdownMenuItem>
          </template>

          <ToneBox
            v-if="platform.data.value.photo_url && platform.data.value.image_url"
            :tone="platform.data.value.image_tone"
            class="inline-flex rounded p-1"
          >
            <img
              :src="platform.data.value.image_url"
              :alt="platform.data.value.name"
              class="h-8 w-auto max-w-56 object-contain object-left"
              data-testid="platform-logo"
            />
          </ToneBox>
          <HeroStats :extra="stats" />
          <ul
            v-if="
              platform.data.value.manufacturer ||
              platform.data.value.predecessors.length ||
              platform.data.value.successors.length
            "
            class="flex flex-wrap items-center gap-x-4 gap-y-2 text-sm text-muted-foreground"
            data-testid="platform-facts"
          >
            <li v-if="platform.data.value.manufacturer" class="inline-flex items-center gap-1.5">
              <Building2 class="size-3.5" />
              <RouterLink
                v-if="platform.data.value.manufacturer_company"
                :to="termPage('companies', platform.data.value.manufacturer_company.id)"
                class="text-foreground hover:underline"
                data-testid="platform-manufacturer"
              >
                {{ platform.data.value.manufacturer }}
              </RouterLink>
              <span v-else>{{ platform.data.value.manufacturer }}</span>
            </li>
            <li
              v-if="platform.data.value.predecessors.length"
              class="inline-flex flex-wrap items-center gap-1.5"
              data-testid="platform-predecessors"
            >
              <ArrowLeft class="size-3.5" /> {{ t('platforms.page.predecessors') }}
              <RouterLink
                v-for="p in platform.data.value.predecessors"
                :key="p.id"
                :to="platformPage(p.id)"
              >
                <PlatformBadge :platform="p" />
              </RouterLink>
            </li>
            <li
              v-if="platform.data.value.successors.length"
              class="inline-flex flex-wrap items-center gap-1.5"
              data-testid="platform-successors"
            >
              <ArrowRight class="size-3.5" /> {{ t('platforms.page.successors') }}
              <RouterLink
                v-for="p in platform.data.value.successors"
                :key="p.id"
                :to="platformPage(p.id)"
              >
                <PlatformBadge :platform="p" />
              </RouterLink>
            </li>
          </ul>

          <div v-if="platform.data.value.description">
            <p
              v-if="otherLanguage"
              class="mb-1 font-mono text-[11px] tracking-wider text-muted-foreground uppercase"
              data-testid="platform-description-language"
            >
              {{ t('terms.onlyIn', { language: otherLanguage }) }}
            </p>
            <p
              class="text-sm leading-relaxed whitespace-pre-line text-muted-foreground"
              :class="!expanded && 'line-clamp-5'"
              data-testid="platform-description"
            >
              {{ platform.data.value.description }}
            </p>
            <button
              v-if="longDescription"
              type="button"
              class="mt-1 text-xs text-primary hover:underline"
              @click="expanded = !expanded"
            >
              {{ expanded ? t('works.less') : t('works.more') }}
            </button>
          </div>
          <div v-else-if="auth.isAdmin" class="flex flex-wrap gap-x-4 gap-y-1">
            <RouterLink
              :to="edit"
              class="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
              data-testid="platform-add-description"
            >
              <Plus class="size-3.5" /> {{ t('terms.addDescription') }}
            </RouterLink>
            <RouterLink
              v-for="d in describers"
              :key="d.name"
              :to="describeRoute('platforms', platformId, d.name)"
              class="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
              :data-testid="`platform-describe-empty-${d.name}`"
            >
              <BookOpen class="size-3.5" />
              {{ t('terms.describe.menu', { source: d.label }) }}
            </RouterLink>
          </div>
        </DetailHero>

        <section v-if="games.data.value?.related.length" data-testid="platform-related">
          <h2 class="mb-2 font-mono text-[11px] tracking-wider text-muted-foreground uppercase">
            {{ t('terms.related') }}
          </h2>
          <TermChips :terms="games.data.value.related" />
        </section>

        <section data-testid="platform-games">
          <div class="mb-3 flex flex-wrap items-center gap-x-4 gap-y-2">
            <h2 class="flex items-baseline gap-2 text-sm font-semibold">
              {{ t('terms.games') }}
              <span class="tabular font-mono text-xs text-muted-foreground">{{
                shown.length
              }}</span>
            </h2>
            <div class="ml-auto flex items-center gap-4">
              <label
                v-if="libraryId && ownedCount"
                class="flex items-center gap-2 text-xs text-muted-foreground"
              >
                <Switch v-model="onlyOwned" data-testid="platform-only-owned" />
                {{ t('terms.onlyOwned') }}
              </label>
              <div class="inline-flex rounded-md border p-0.5" role="group">
                <button
                  v-for="s in ['year', 'title'] as const"
                  :key="s"
                  type="button"
                  :aria-pressed="sort === s"
                  :data-testid="`platform-sort-${s}`"
                  :class="
                    cn(
                      'rounded-sm px-2 py-0.5 text-xs text-muted-foreground transition hover:text-foreground',
                      sort === s && 'bg-accent text-foreground',
                    )
                  "
                  @click="sort = s"
                >
                  {{ t(`terms.sort.${s}`) }}
                </button>
              </div>
            </div>
          </div>
          <div v-if="games.isPending.value" class="grid grid-cols-4 gap-2">
            <Skeleton v-for="i in 4" :key="i" class="aspect-[3/4] rounded-md" />
          </div>
          <div
            v-else-if="shown.length"
            class="grid grid-cols-[repeat(auto-fill,minmax(6.5rem,1fr))] items-end gap-x-1 gap-y-3 @2xl:grid-cols-[repeat(auto-fill,minmax(8.5rem,1fr))] @2xl:gap-x-2 @2xl:gap-y-4"
          >
            <TermWorkCard v-for="work in shown" :key="work.id" :work="work" />
          </div>
          <p
            v-else
            class="rounded-lg border border-dashed p-4 text-sm text-muted-foreground"
            data-testid="platform-unused"
          >
            {{ allWorks.length ? t('terms.noneOwned') : t('platforms.page.unused') }}
          </p>
        </section>
      </template>
      <div v-else class="flex flex-col gap-6 @lg:flex-row" data-testid="page-pending">
        <Skeleton class="mx-auto size-40 rounded-xl @lg:mx-0 @lg:size-48" />
        <div class="flex-1 space-y-3">
          <Skeleton class="h-8 w-2/3" />
          <Skeleton class="h-5 w-1/3" />
          <Skeleton class="h-20 w-full" />
        </div>
      </div>
    </div>
  </div>
</template>
