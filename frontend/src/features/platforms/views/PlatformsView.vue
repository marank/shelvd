<script setup lang="ts">
import { ChevronRight, LayoutGrid, Plus, Search, Sheet } from '@lucide/vue'
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import PlatformBadge from '@/components/app/PlatformBadge.vue'
import ToneBox from '@/components/app/ToneBox.vue'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Spinner } from '@/components/ui/spinner'
import { usePlatforms } from '@/features/library/composables/useReference'
import { platformColor } from '@/lib/labels'
import { platformPage } from '@/lib/terms'
import { cn } from '@/lib/utils'
import { useAuthStore } from '@/stores/auth'
import { useUiStore, type PlatformLayout } from '@/stores/ui'
import PlatformMark from '../components/PlatformMark.vue'
import type { PlatformListEntry } from '../composables/usePlatforms'

/** Every platform of the catalog by manufacturer – as a table (mark, name, generation,
 * years, games) or as tiles with a photo of the device. Each opens its page. */
const { t } = useI18n()
const auth = useAuthStore()
const ui = useUiStore()
const platforms = usePlatforms()
const query = ref('')
const LAYOUTS: { value: PlatformLayout; icon: typeof Sheet }[] = [
  { value: 'table', icon: Sheet },
  { value: 'tiles', icon: LayoutGrid },
]

const list = computed(() => (platforms.data.value ?? []) as PlatformListEntry[])
const groups = computed(() => {
  const q = query.value.trim().toLowerCase()
  const byMaker = new Map<string, PlatformListEntry[]>()
  for (const p of list.value) {
    const text = `${p.name} ${p.short_name} ${p.manufacturer}`.toLowerCase()
    if (q && !text.includes(q)) continue
    const maker = p.manufacturer || t('platforms.noManufacturer')
    byMaker.set(maker, [...(byMaker.get(maker) ?? []), p])
  }
  return [...byMaker.entries()]
})
const shown = computed(() => groups.value.reduce((n, [, l]) => n + l.length, 0))

/** "2017", "2001–2007". */
const years = (p: PlatformListEntry) =>
  p.discontinued ? `${p.release_year ?? '?'}–${p.discontinued}` : String(p.release_year ?? '')
const subline = (p: PlatformListEntry) =>
  [p.short_name, t(`choices.media_type.${p.media_type}`)].filter(Boolean).join(' · ')
</script>

<template>
  <div class="flex min-w-0 flex-1 flex-col overflow-y-auto" data-testid="PlatformsView">
    <header class="flex flex-wrap items-center justify-between gap-3 border-b px-4 py-3 md:px-6">
      <div class="min-w-0">
        <h1 class="text-lg font-semibold tracking-tight">{{ t('platforms.title') }}</h1>
        <p class="text-sm text-muted-foreground">{{ t('platforms.subtitle') }}</p>
      </div>
      <Button v-if="auth.isAdmin" as-child>
        <RouterLink :to="{ name: 'platform-new' }" data-testid="platform-new">
          <Plus /> {{ t('platforms.add') }}
        </RouterLink>
      </Button>
    </header>

    <div class="mx-auto grid w-full max-w-5xl gap-6 p-4 md:px-6">
      <div class="flex flex-wrap items-center gap-3">
        <label class="relative flex min-w-48 flex-1 items-center">
          <Search class="pointer-events-none absolute left-2.5 size-4 text-muted-foreground" />
          <span class="sr-only">{{ t('platforms.search') }}</span>
          <Input
            v-model="query"
            class="pl-8"
            :placeholder="t('platforms.search')"
            data-testid="platform-search"
          />
        </label>
        <span
          v-if="list.length"
          class="tabular font-mono text-[11px] tracking-wider text-muted-foreground uppercase"
          data-testid="platform-count"
        >
          {{ t('platforms.count', { n: shown }, shown) }}
        </span>
        <div
          class="inline-flex rounded-md border p-0.5"
          role="group"
          :aria-label="t('platforms.layout')"
        >
          <button
            v-for="l in LAYOUTS"
            :key="l.value"
            type="button"
            :aria-pressed="ui.platformLayout === l.value"
            :title="t(`platforms.layouts.${l.value}`)"
            :class="
              cn(
                'rounded-sm p-1.5 text-muted-foreground transition hover:text-foreground',
                ui.platformLayout === l.value && 'bg-accent text-foreground',
              )
            "
            :data-testid="`platform-layout-${l.value}`"
            @click="ui.platformLayout = l.value"
          >
            <component :is="l.icon" class="size-4" />
            <span class="sr-only">{{ t(`platforms.layouts.${l.value}`) }}</span>
          </button>
        </div>
      </div>

      <div v-if="platforms.isPending.value" class="flex justify-center py-10">
        <Spinner class="size-6" />
      </div>
      <Alert v-else-if="platforms.isError.value" variant="destructive">
        <AlertDescription>{{ platforms.error.value?.message }}</AlertDescription>
      </Alert>
      <p v-else-if="!groups.length" class="text-sm text-muted-foreground">
        {{ t('platforms.none') }}
      </p>

      <section
        v-for="[maker, entries] in groups"
        :key="maker"
        class="grid gap-2"
        :data-testid="`maker-${maker}`"
      >
        <h2
          class="flex items-center gap-2 font-mono text-[11px] tracking-wider text-muted-foreground uppercase"
        >
          <span
            class="size-2 rounded-full"
            :style="{ backgroundColor: platformColor(entries[0]!) }"
          />
          {{ maker }}
          <span class="tabular">· {{ entries.length }}</span>
        </h2>

        <div
          v-if="ui.platformLayout === 'table'"
          class="overflow-hidden rounded-lg border bg-card"
          role="table"
        >
          <div
            class="hidden grid-cols-[2.25rem_minmax(0,1fr)_5.5rem_7rem_4.5rem_1rem] items-center gap-3 border-b bg-muted/40 px-3 py-1.5 font-mono text-[10px] tracking-wider text-muted-foreground uppercase sm:grid"
            role="row"
          >
            <span role="columnheader" class="col-span-2">{{ t('platforms.columns.name') }}</span>
            <span role="columnheader">{{ t('platforms.columns.generation') }}</span>
            <span role="columnheader">{{ t('platforms.columns.years') }}</span>
            <span role="columnheader" class="text-right">{{ t('platforms.columns.games') }}</span>
            <span />
          </div>
          <RouterLink
            v-for="p in entries"
            :key="p.id"
            :to="platformPage(p.id)"
            class="grid grid-cols-[2.25rem_minmax(0,1fr)_auto_1rem] items-center gap-3 border-b px-3 py-2 transition-colors last:border-b-0 hover:bg-muted/50 sm:grid-cols-[2.25rem_minmax(0,1fr)_5.5rem_7rem_4.5rem_1rem]"
            role="row"
            data-testid="platform-row"
          >
            <PlatformMark :platform="p" class="size-9" />
            <span class="grid min-w-0" role="cell">
              <span class="truncate text-sm font-medium">{{ p.name }}</span>
              <span class="truncate text-xs text-muted-foreground">{{ subline(p) }}</span>
            </span>
            <span
              class="tabular hidden font-mono text-xs text-muted-foreground sm:block"
              role="cell"
            >
              {{ p.generation ? t('platforms.generationN', { n: p.generation }) : '–' }}
            </span>
            <span
              class="tabular hidden font-mono text-xs text-muted-foreground sm:block"
              role="cell"
            >
              {{ years(p) || '–' }}
            </span>
            <span class="tabular text-right font-mono text-xs" role="cell">
              {{ p.game_count }}
            </span>
            <ChevronRight class="size-4 text-muted-foreground" />
          </RouterLink>
        </div>

        <ul v-else class="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
          <li v-for="p in entries" :key="p.id">
            <RouterLink
              :to="platformPage(p.id)"
              class="group grid h-full overflow-hidden rounded-lg border bg-card transition hover:border-primary/50 hover:shadow-sm"
              data-testid="platform-tile"
            >
              <ToneBox
                :tone="p.photo_url ? p.photo_tone : p.image_tone"
                :photo="!!p.photo_url"
                class="spotlight relative grid grid-cols-1 grid-rows-1 aspect-[4/3] place-items-center border-b bg-muted/30"
                :style="{ borderTop: `3px solid ${platformColor(p)}` }"
              >
                <img
                  v-if="p.photo_url"
                  :src="p.photo_url"
                  :alt="p.name"
                  loading="lazy"
                  class="max-h-full max-w-full object-contain p-3 transition group-hover:scale-[1.03]"
                  data-testid="platform-tile-photo"
                />
                <img
                  v-else-if="p.image_url"
                  :src="p.image_url"
                  :alt="p.name"
                  loading="lazy"
                  class="max-h-[55%] max-w-[75%] object-contain"
                  data-testid="platform-tile-logo"
                />
                <PlatformMark v-else :platform="p" class="size-16" />
              </ToneBox>
              <span class="grid gap-1.5 p-2.5">
                <span class="line-clamp-2 text-sm leading-tight font-medium">{{ p.name }}</span>
                <span class="flex items-center justify-between gap-2">
                  <PlatformBadge :platform="p" />
                  <span class="tabular font-mono text-[11px] text-muted-foreground">
                    {{ years(p) }}
                  </span>
                </span>
                <span class="text-xs text-muted-foreground">
                  {{ t('platforms.games', { n: p.game_count }, p.game_count) }}
                </span>
              </span>
            </RouterLink>
          </li>
        </ul>
      </section>
    </div>
  </div>
</template>
