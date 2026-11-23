<script setup lang="ts">
// "Alle Ausgaben": every release of the game – on wide screens as a timeline (a row per
// platform, a dot per release at its date: filled = you have it, ringed = the one this
// page is about), always as a list below (date, platform, region, edition, your copies).
// Each opens its release.
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import PlatformBadge from '@/components/app/PlatformBadge.vue'
import ReleaseDate from '@/components/app/ReleaseDate.vue'
import type { Release } from '@/api/types'
import { platformColor } from '@/lib/labels'

const props = defineProps<{
  releases: Release[]
  /** Copies in this library per release id. */
  owned: Record<string, number>
  current?: string
}>()
const { t, n } = useI18n()

const time = (r: Release) => (r.release_date ? Date.parse(r.sort_date) : NaN)
const dated = computed(() => props.releases.filter((r) => !Number.isNaN(time(r))))
const range = computed(() => {
  const times = dated.value.map(time)
  const from = new Date(Math.min(...times)).getUTCFullYear()
  const to = new Date(Math.max(...times)).getUTCFullYear() + 1
  return { from, to, start: Date.UTC(from, 0, 1), end: Date.UTC(to, 0, 1) }
})
/** Year marks: every year, or every few when the game spans decades. */
const years = computed(() => {
  const { from, to } = range.value
  const step = Math.max(1, Math.ceil((to - from) / 8))
  const marks: { year: number; at: string }[] = []
  for (let year = from; year <= to; year += step)
    marks.push({ year, at: `${((Date.UTC(year, 0, 1) - range.value.start) / span()) * 100}%` })
  return marks
})
const span = () => Math.max(range.value.end - range.value.start, 1)
const rows = computed(() => {
  const byPlatform = new Map<string, { platform: Release['platform']; releases: Release[] }>()
  for (const release of dated.value) {
    const row = byPlatform.get(release.platform.id) ?? { platform: release.platform, releases: [] }
    row.releases.push(release)
    byPlatform.set(release.platform.id, row)
  }
  return [...byPlatform.values()].map((row) => ({
    ...row,
    color: platformColor(row.platform),
    dots: row.releases.map((release) => ({
      release,
      at: `${((time(release) - range.value.start) / span()) * 100}%`,
    })),
  }))
})
const sorted = computed(() =>
  [...props.releases].sort((a, b) => a.sort_date.localeCompare(b.sort_date)),
)
const describe = (r: Release) =>
  [r.platform.short_name || r.platform.name, r.region.toUpperCase(), r.edition]
    .filter(Boolean)
    .join(' · ')
</script>

<template>
  <div class="space-y-4" data-testid="release-timeline">
    <div v-if="dated.length > 1" class="hidden @2xl:block" data-testid="timeline-chart">
      <div
        v-for="row in rows"
        :key="row.platform.id"
        class="grid grid-cols-[7rem_1fr] items-center"
      >
        <span class="truncate pr-2 text-xs text-muted-foreground">{{ row.platform.name }}</span>
        <div class="relative h-8 border-b border-dashed">
          <RouterLink
            v-for="dot in row.dots"
            :key="dot.release.id"
            :to="{ name: 'release', params: { releaseId: dot.release.id } }"
            class="absolute top-1/2 size-3 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 transition hover:scale-125"
            :class="dot.release.id === current && 'ring-4 ring-primary/25'"
            :style="{
              left: dot.at,
              borderColor: row.color,
              background: owned[dot.release.id] ? row.color : 'var(--background)',
            }"
            :title="describe(dot.release)"
            :aria-label="describe(dot.release)"
            data-testid="timeline-dot"
          />
        </div>
      </div>
      <div class="grid grid-cols-[7rem_1fr]">
        <span />
        <div class="relative h-5 font-mono text-[11px] text-muted-foreground">
          <span
            v-for="mark in years"
            :key="mark.year"
            class="absolute top-1 -translate-x-1/2 tabular"
            :style="{ left: mark.at }"
            >{{ mark.year }}</span
          >
        </div>
      </div>
    </div>

    <ul class="divide-y rounded-lg border text-sm" data-testid="release-list">
      <li v-for="release in sorted" :key="release.id">
        <RouterLink
          :to="{ name: 'release', params: { releaseId: release.id } }"
          class="grid grid-cols-[6.5rem_1fr_auto] items-center gap-3 px-3 py-2 hover:bg-muted/50"
          :class="release.id === current && 'bg-muted/60'"
          :data-current="release.id === current || undefined"
          data-testid="release-row"
        >
          <span class="font-mono text-xs tabular text-muted-foreground">
            <ReleaseDate :release="release" />
          </span>
          <span class="flex min-w-0 flex-wrap items-center gap-1.5">
            <PlatformBadge :platform="release.platform" />
            <span class="font-mono text-[11px] text-muted-foreground uppercase">{{
              release.region
            }}</span>
            <span v-if="release.edition" class="truncate">{{ release.edition }}</span>
            <span
              v-if="release.release_number"
              class="font-mono text-xs tabular text-muted-foreground"
              >#{{ release.release_number }}</span
            >
          </span>
          <span class="text-xs text-muted-foreground">
            <template v-if="release.id === current">{{ t('game.thisOne') }}</template>
            <template v-else-if="owned[release.id]">{{
              t('game.owned', { n: n(owned[release.id]!) }, owned[release.id]!)
            }}</template>
          </span>
        </RouterLink>
      </li>
    </ul>
  </div>
</template>
