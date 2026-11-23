<script setup lang="ts">
import { ChevronRight, LayoutGrid, Search, Sheet } from '@lucide/vue'
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Input } from '@/components/ui/input'
import { Spinner } from '@/components/ui/spinner'
import { countryName } from '@/lib/displayNames'
import { TERM_ICONS, termPage } from '@/lib/terms'
import { cn } from '@/lib/utils'
import { useUiStore, type OverviewSort, type PlatformLayout } from '@/stores/ui'
import TermMark from '../components/TermMark.vue'
import { useTermList, type TermListEntry } from '../composables/useTermPages'
import { useTermRoute } from '../composables/useTermRoute'

/** Every company, genre, franchise or series of the catalog – like the platforms page:
 * as a table (mark, name with what it is, games) or as tiles, by initial or by how often
 * it's used. */
const { t, locale } = useI18n()
const { kind } = useTermRoute()
const ui = useUiStore()
const terms = useTermList(kind)
const query = ref('')
watch(kind, () => (query.value = ''))
const LAYOUTS: { value: PlatformLayout; icon: typeof Sheet }[] = [
  { value: 'table', icon: Sheet },
  { value: 'tiles', icon: LayoutGrid },
]
const SORTS: OverviewSort[] = ['name', 'uses']

const collator = new Intl.Collator(undefined, { sensitivity: 'base', numeric: true })
const initial = (name: string) => {
  const first = name.trim().charAt(0).toLocaleUpperCase()
  return /\p{L}/u.test(first) ? first : '#'
}
const matching = computed(() => {
  const q = query.value.trim().toLowerCase()
  return (terms.data.value ?? []).filter((term) => !q || term.name.toLowerCase().includes(q))
})
/** By initial when sorted by name; one group, most used first, otherwise. */
const groups = computed(() => {
  if (ui.termSort === 'uses') {
    const list = [...matching.value].sort(
      (a, b) => b.uses - a.uses || collator.compare(a.name, b.name),
    )
    return list.length ? ([['', list]] as [string, TermListEntry[]][]) : []
  }
  const byInitial = new Map<string, TermListEntry[]>()
  for (const term of [...matching.value].sort((a, b) => collator.compare(a.name, b.name))) {
    const key = initial(term.name)
    byInitial.set(key, [...(byInitial.get(key) ?? []), term])
  }
  return [...byInitial.entries()]
})

/** What it is, briefly: a company's country and founding year, else its description. */
const subline = (term: TermListEntry) =>
  kind.value === 'companies' && (term.country || term.founded)
    ? [term.country && countryName(term.country, locale.value), term.founded]
        .filter(Boolean)
        .join(' · ')
    : term.summary
</script>

<template>
  <div class="flex min-w-0 flex-1 flex-col overflow-y-auto" data-testid="TermsView">
    <header class="flex flex-wrap items-center gap-3 border-b px-4 py-3 md:px-6">
      <component :is="TERM_ICONS[kind]" class="size-5 text-muted-foreground" />
      <div class="min-w-0">
        <h1 class="text-lg font-semibold tracking-tight">{{ t(`terms.${kind}.title`) }}</h1>
        <p class="text-sm text-muted-foreground">{{ t(`terms.${kind}.subtitle`) }}</p>
      </div>
    </header>

    <div class="mx-auto grid w-full max-w-5xl gap-6 p-4 md:px-6">
      <div class="flex flex-wrap items-center gap-3">
        <label class="relative flex min-w-48 flex-1 items-center">
          <Search class="pointer-events-none absolute left-2.5 size-4 text-muted-foreground" />
          <span class="sr-only">{{ t('terms.search') }}</span>
          <Input
            v-model="query"
            class="pl-8"
            :placeholder="t('terms.search')"
            data-testid="term-search"
          />
        </label>
        <span
          v-if="terms.data.value"
          class="tabular font-mono text-[11px] tracking-wider text-muted-foreground uppercase"
          data-testid="term-count"
        >
          {{ t('terms.count', { n: matching.length }, matching.length) }}
        </span>
        <div
          class="inline-flex rounded-md border p-0.5"
          role="group"
          :aria-label="t('terms.sortBy')"
        >
          <button
            v-for="s in SORTS"
            :key="s"
            type="button"
            :aria-pressed="ui.termSort === s"
            :class="
              cn(
                'rounded-sm px-2 py-1 text-xs text-muted-foreground transition hover:text-foreground',
                ui.termSort === s && 'bg-accent text-foreground',
              )
            "
            :data-testid="`term-overview-sort-${s}`"
            @click="ui.termSort = s"
          >
            {{ t(`terms.overviewSort.${s}`) }}
          </button>
        </div>
        <div
          class="inline-flex rounded-md border p-0.5"
          role="group"
          :aria-label="t('platforms.layout')"
        >
          <button
            v-for="l in LAYOUTS"
            :key="l.value"
            type="button"
            :aria-pressed="ui.termLayout === l.value"
            :title="t(`platforms.layouts.${l.value}`)"
            :class="
              cn(
                'rounded-sm p-1.5 text-muted-foreground transition hover:text-foreground',
                ui.termLayout === l.value && 'bg-accent text-foreground',
              )
            "
            :data-testid="`term-layout-${l.value}`"
            @click="ui.termLayout = l.value"
          >
            <component :is="l.icon" class="size-4" />
            <span class="sr-only">{{ t(`platforms.layouts.${l.value}`) }}</span>
          </button>
        </div>
      </div>

      <div v-if="terms.isPending.value" class="flex justify-center py-10">
        <Spinner class="size-6" />
      </div>
      <Alert v-else-if="terms.isError.value" variant="destructive">
        <AlertDescription>{{ terms.error.value?.message }}</AlertDescription>
      </Alert>
      <p v-else-if="!groups.length" class="text-sm text-muted-foreground" data-testid="no-terms">
        {{ t('terms.none') }}
      </p>

      <section v-for="[letter, list] in groups" :key="letter" class="grid gap-2">
        <h2
          v-if="letter"
          class="font-mono text-[11px] tracking-wider text-muted-foreground uppercase"
        >
          {{ letter }} <span class="tabular">· {{ list.length }}</span>
        </h2>

        <div v-if="ui.termLayout === 'table'" class="overflow-hidden rounded-lg border bg-card">
          <RouterLink
            v-for="term in list"
            :key="term.id"
            :to="termPage(kind, term.id)"
            class="grid grid-cols-[2.25rem_minmax(0,1fr)_auto_1rem] items-center gap-3 border-b px-3 py-2 transition-colors last:border-b-0 hover:bg-muted/50"
            data-testid="term-row"
          >
            <TermMark
              :name="term.name"
              :image-url="term.image_url"
              :tone="term.image_tone"
              class="size-9"
            />
            <span class="grid min-w-0">
              <span class="truncate text-sm font-medium">{{ term.name }}</span>
              <span v-if="subline(term)" class="truncate text-xs text-muted-foreground">
                {{ subline(term) }}
              </span>
            </span>
            <span
              class="tabular text-right font-mono text-xs text-muted-foreground"
              :title="t(`terms.${kind}.uses`, term.uses)"
            >
              {{ term.uses }}
            </span>
            <ChevronRight class="size-4 text-muted-foreground" />
          </RouterLink>
        </div>

        <ul v-else class="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
          <li v-for="term in list" :key="term.id">
            <RouterLink
              :to="termPage(kind, term.id)"
              class="group grid h-full content-start overflow-hidden rounded-lg border bg-card transition hover:border-primary/50 hover:shadow-sm"
              data-testid="term-tile"
            >
              <TermMark
                :name="term.name"
                :image-url="term.image_url"
                :tone="term.image_tone"
                class="aspect-[4/3] w-full rounded-none border-0 border-b"
              />
              <span class="grid gap-1 p-2.5">
                <span class="line-clamp-2 text-sm leading-tight font-medium">{{ term.name }}</span>
                <span v-if="subline(term)" class="line-clamp-2 text-xs text-muted-foreground">
                  {{ subline(term) }}
                </span>
                <span class="tabular font-mono text-[11px] text-muted-foreground">
                  {{ t(`terms.${kind}.usesShort`, { n: term.uses }, term.uses) }}
                </span>
              </span>
            </RouterLink>
          </li>
        </ul>
      </section>
    </div>
  </div>
</template>
