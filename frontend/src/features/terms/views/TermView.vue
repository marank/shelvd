<script setup lang="ts">
import { useAuthStore } from '@/stores/auth'
import {
  BookOpen,
  Building2,
  Crown,
  ExternalLink,
  ImagePlus,
  MapPin,
  Merge,
  Pencil,
  Plus,
} from '@lucide/vue'
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import BackButton from '@/components/app/BackButton.vue'
import DetailHero from '@/components/app/DetailHero.vue'
import HeroStats from '@/components/app/HeroStats.vue'
import TermChips from '@/components/app/TermChips.vue'
import PlatformBadge from '@/components/app/PlatformBadge.vue'
import { DropdownMenuItem } from '@/components/ui/dropdown-menu'
import { Skeleton } from '@/components/ui/skeleton'
import { Switch } from '@/components/ui/switch'
import { useCurrentLibrary } from '@/features/library/composables/useCurrentLibrary'
import { useLibrary } from '@/features/library/composables/useLibraries'
import { TERM_ICONS, termList, termPage } from '@/lib/terms'
import { countryName, languageName } from '@/lib/displayNames'
import { cn } from '@/lib/utils'
import TermVisual from '../components/TermVisual.vue'
import TermWorkCard from '../components/TermWorkCard.vue'
import { useOwned } from '@/features/library/composables/useOwned'
import { termGames, useDescribers, useTerm, type TermWork } from '../composables/useTermPages'
import { useTermRoute } from '../composables/useTermRoute'

/** A company's, genre's or series' page: picture, description, figures, what its games
 * have in common, and the games themselves – from the whole catalog, the current
 * library's marked. A company's games can be narrowed to developed or published. */
const { t, locale } = useI18n()
const { kind, termId } = useTermRoute()
const auth = useAuthStore()
const term = useTerm(kind, termId)
const { id: libraryId } = useCurrentLibrary()
const library = useLibrary(libraryId)
const owned = useOwned(libraryId)
const copies = (work: TermWork) => owned.data.value?.works.get(work.id) ?? 0

type Role = 'all' | 'developed' | 'published'
const role = ref<Role>('all')
const sort = ref<'year' | 'title'>('year')
const onlyOwned = ref(false)
watch(termId, () => ((role.value = 'all'), (onlyOwned.value = false)))

const allWorks = computed(() => termGames(term.data.value))
const roles = computed(() => {
  const data = term.data.value
  if (kind.value !== 'companies' || !data?.works.length || !data.published.length) return []
  return [
    { key: 'all' as const, count: allWorks.value.length },
    { key: 'developed' as const, count: data.works.length },
    { key: 'published' as const, count: data.published.length },
  ]
})
const collator = new Intl.Collator(undefined, { sensitivity: 'base', numeric: true })
const shown = computed(() => {
  const data = term.data.value
  if (!data) return []
  const list =
    role.value === 'developed'
      ? data.works
      : role.value === 'published'
        ? data.published
        : allWorks.value
  const filtered = onlyOwned.value ? list.filter((w) => copies(w) > 0) : [...list]
  return sort.value === 'title'
    ? filtered.sort((a, b) => collator.compare(a.title, b.title))
    : filtered.sort((a, b) => (a.year ?? 9999) - (b.year ?? 9999))
})

const platforms = computed(() => {
  const seen = new Map<string, TermWork['platforms'][number]>()
  for (const work of allWorks.value) for (const p of work.platforms) seen.set(p.id, p)
  return [...seen.values()].sort((a, b) => (a.release_year ?? 0) - (b.release_year ?? 0))
})
const years = computed(() => {
  const list = allWorks.value.map((w) => w.year).filter((y): y is number => !!y)
  if (!list.length) return ''
  const [first, last] = [Math.min(...list), Math.max(...list)]
  return first === last ? String(first) : `${first}–${last}`
})
/** A company's details: years and country as figures, seat, website, parent below. */
const details = computed(() => term.data.value?.company ?? null)
const lifetime = computed(() => {
  const d = details.value
  if (!d?.founded && !d?.dissolved) return ''
  return d.dissolved ? `${d.founded ?? '?'}–${d.dissolved}` : String(d.founded)
})
const facts = computed(() => [
  ...(lifetime.value
    ? [
        {
          key: 'founded',
          label: details.value?.dissolved ? t('terms.details.existed') : t('terms.details.founded'),
          value: lifetime.value,
        },
      ]
    : []),
  ...(details.value?.country
    ? [
        {
          key: 'country',
          label: t('terms.details.country'),
          value: countryName(details.value.country, locale.value),
        },
      ]
    : []),
])
/** "https://www.nintendo.co.jp/…" → "nintendo.co.jp" (the backend only stores http(s)). */
const websiteHost = computed(() =>
  (details.value?.website ?? '').replace(/^https?:\/\/(www\.)?/, '').replace(/[/?#].*$/, ''),
)
/** A franchise's series, as chips. */
const parts = computed(() =>
  (term.data.value?.parts ?? []).map((s) => ({ kind: 'series' as const, ...s })),
)
const subsidiaries = computed(() =>
  (details.value?.subsidiaries ?? []).map((s) => ({ kind: 'companies' as const, ...s })),
)
const ownedCount = computed(() => allWorks.value.filter((w) => copies(w) > 0).length)
const stats = computed(() => [
  ...facts.value,
  { key: 'games', label: t('terms.games'), value: allWorks.value.length },
  ...(years.value ? [{ key: 'years', label: t('terms.years'), value: years.value }] : []),
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
])

/** Where a company's or series' text can come from (Wikipedia, IGDB), if switched on. */
const describers = useDescribers(kind)
const describeTo = (source: string) => ({
  name: `${kind.value}-description`,
  params: { termId: termId.value, source },
})

/** The text is in another language than the reader's (theirs has none). */
const otherLanguage = computed(() => {
  const code = term.data.value?.description_language
  return code && code !== locale.value ? languageName(code, locale.value) : ''
})
const expanded = ref(false)
const longDescription = computed(() => {
  const text = term.data.value?.description ?? ''
  return text.length > 400 || text.split('\n').length > 5
})
</script>

<template>
  <div class="flex-1 overflow-y-auto" data-testid="TermView">
    <div class="@container mx-auto max-w-5xl space-y-8 px-4 py-4 md:px-6 md:py-6">
      <BackButton :fallback="termList(kind)" />

      <p v-if="term.isError.value" class="py-16 text-center text-muted-foreground">
        {{ t('errors.notFound') }}
      </p>
      <template v-else-if="term.data.value">
        <DetailHero :title="term.data.value.name" :menu-label="t('terms.actions')" testid="term">
          <template #visual>
            <TermVisual
              :kind="kind"
              :name="term.data.value.name"
              :image-url="term.data.value.image_url"
              :tone="term.data.value.image_tone"
              :works="allWorks"
            />
          </template>
          <template #kicker>
            <RouterLink
              :to="termList(kind)"
              class="inline-flex items-center gap-1.5 hover:text-foreground"
            >
              <component :is="TERM_ICONS[kind]" class="size-3.5" />
              {{ t(`terms.${kind}.one`) }}
            </RouterLink>
          </template>
          <template v-if="auth.isAdmin" #menu>
            <DropdownMenuItem as-child>
              <RouterLink
                :to="{ name: `${kind}-edit`, params: { termId } }"
                data-testid="term-edit"
              >
                <Pencil class="size-4" /> {{ t('actions.edit') }}
              </RouterLink>
            </DropdownMenuItem>
            <DropdownMenuItem as-child>
              <RouterLink
                :to="{ name: `${kind}-merge`, params: { termId } }"
                data-testid="term-merge"
              >
                <Merge class="size-4" /> {{ t('terms.mergeMenu') }}
              </RouterLink>
            </DropdownMenuItem>
            <DropdownMenuItem v-for="d in describers" :key="d.name" as-child>
              <RouterLink :to="describeTo(d.name)" :data-testid="`term-describe-${d.name}`">
                <BookOpen class="size-4" />
                {{ t('terms.describe.menu', { source: d.label }) }}
              </RouterLink>
            </DropdownMenuItem>
            <DropdownMenuItem v-if="describers.length" as-child>
              <RouterLink
                :to="{ name: `${kind}-image`, params: { termId } }"
                data-testid="term-choose-image"
              >
                <ImagePlus class="size-4" /> {{ t('terms.images.menu') }}
              </RouterLink>
            </DropdownMenuItem>
          </template>

          <HeroStats :extra="stats" />
          <ul
            v-if="details && (details.headquarters || websiteHost || details.parent)"
            class="flex flex-wrap gap-x-4 gap-y-1 text-sm text-muted-foreground"
            data-testid="term-company"
          >
            <li v-if="details.headquarters" class="inline-flex items-center gap-1.5">
              <MapPin class="size-3.5" /> {{ details.headquarters }}
            </li>
            <li v-if="details.parent" class="inline-flex items-center gap-1.5">
              <Building2 class="size-3.5" />
              {{ t('terms.details.parent') }}
              <RouterLink
                :to="termPage('companies', details.parent.id)"
                class="text-foreground hover:underline"
                data-testid="term-parent"
              >
                {{ details.parent.name }}
              </RouterLink>
            </li>
            <li v-if="websiteHost">
              <a
                :href="details.website"
                target="_blank"
                rel="noopener noreferrer"
                class="inline-flex items-center gap-1.5 hover:text-foreground"
                data-testid="term-website"
              >
                <ExternalLink class="size-3.5" /> {{ websiteHost }}
              </a>
            </li>
          </ul>
          <p
            v-if="term.data.value.franchise"
            class="inline-flex items-center gap-1.5 text-sm text-muted-foreground"
            data-testid="term-franchise"
          >
            <Crown class="size-3.5" /> {{ t('terms.partOf') }}
            <RouterLink
              :to="termPage('franchises', term.data.value.franchise.id)"
              class="text-foreground hover:underline"
            >
              {{ term.data.value.franchise.name }}
            </RouterLink>
          </p>
          <div v-if="platforms.length" class="flex flex-wrap gap-1.5" data-testid="term-platforms">
            <PlatformBadge v-for="p in platforms" :key="p.id" :platform="p" />
          </div>

          <div v-if="term.data.value.description">
            <p
              v-if="otherLanguage"
              class="mb-1 font-mono text-[11px] tracking-wider text-muted-foreground uppercase"
              data-testid="term-description-language"
            >
              {{ t('terms.onlyIn', { language: otherLanguage }) }}
            </p>
            <p
              class="text-sm leading-relaxed whitespace-pre-line text-muted-foreground"
              :class="!expanded && 'line-clamp-5'"
              data-testid="term-description"
            >
              {{ term.data.value.description }}
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
              :to="{ name: `${kind}-edit`, params: { termId } }"
              class="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
              data-testid="term-add-description"
            >
              <Plus class="size-3.5" /> {{ t('terms.addDescription') }}
            </RouterLink>
            <RouterLink
              v-for="d in describers"
              :key="d.name"
              :to="describeTo(d.name)"
              class="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
              :data-testid="`term-describe-empty-${d.name}`"
            >
              <BookOpen class="size-3.5" />
              {{ t('terms.describe.menu', { source: d.label }) }}
            </RouterLink>
          </div>
        </DetailHero>

        <section v-if="parts.length" data-testid="term-parts">
          <h2 class="mb-2 font-mono text-[11px] tracking-wider text-muted-foreground uppercase">
            {{ t('terms.series.title') }}
          </h2>
          <TermChips :terms="parts" />
        </section>

        <section v-if="subsidiaries.length" data-testid="term-subsidiaries">
          <h2 class="mb-2 font-mono text-[11px] tracking-wider text-muted-foreground uppercase">
            {{ t('terms.details.subsidiaries') }}
          </h2>
          <TermChips :terms="subsidiaries" />
        </section>

        <section v-if="term.data.value.related.length" data-testid="term-related">
          <h2 class="mb-2 font-mono text-[11px] tracking-wider text-muted-foreground uppercase">
            {{ t('terms.related') }}
          </h2>
          <TermChips :terms="term.data.value.related" />
        </section>

        <section data-testid="term-games">
          <div class="mb-3 flex flex-wrap items-center gap-x-4 gap-y-2">
            <h2 class="flex items-baseline gap-2 text-sm font-semibold">
              {{ t('terms.games') }}
              <span class="tabular font-mono text-xs text-muted-foreground">{{
                shown.length
              }}</span>
            </h2>
            <div
              v-if="roles.length"
              class="inline-flex rounded-md border p-0.5"
              role="group"
              data-testid="term-roles"
            >
              <button
                v-for="r in roles"
                :key="r.key"
                type="button"
                :aria-pressed="role === r.key"
                :data-testid="`term-role-${r.key}`"
                :class="
                  cn(
                    'rounded-sm px-2 py-0.5 text-xs text-muted-foreground transition hover:text-foreground',
                    role === r.key && 'bg-accent text-foreground',
                  )
                "
                @click="role = r.key"
              >
                {{ t(`terms.role.${r.key}`) }}
                <span class="tabular font-mono text-[11px] opacity-70">{{ r.count }}</span>
              </button>
            </div>
            <div class="ml-auto flex items-center gap-4">
              <label
                v-if="libraryId && ownedCount"
                class="flex items-center gap-2 text-xs text-muted-foreground"
              >
                <Switch v-model="onlyOwned" data-testid="term-only-owned" />
                {{ t('terms.onlyOwned') }}
              </label>
              <div class="inline-flex rounded-md border p-0.5" role="group">
                <button
                  v-for="s in ['year', 'title'] as const"
                  :key="s"
                  type="button"
                  :aria-pressed="sort === s"
                  :data-testid="`term-sort-${s}`"
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
          <div
            v-if="shown.length"
            class="grid grid-cols-[repeat(auto-fill,minmax(6.5rem,1fr))] items-end gap-x-1 gap-y-3 @2xl:grid-cols-[repeat(auto-fill,minmax(8.5rem,1fr))] @2xl:gap-x-2 @2xl:gap-y-4"
          >
            <TermWorkCard v-for="work in shown" :key="work.id" :work="work" />
          </div>
          <p
            v-else
            class="rounded-lg border border-dashed p-4 text-sm text-muted-foreground"
            data-testid="term-unused"
          >
            {{ allWorks.length ? t('terms.noneOwned') : t('terms.unused') }}
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
