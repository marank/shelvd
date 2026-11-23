<script setup lang="ts">
import { useAuthStore } from '@/stores/auth'
import { CalendarClock } from '@lucide/vue'
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { toast } from 'vue-sonner'
import type { Tracking } from '@/api/types'
import { Empty, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from '@/components/ui/empty'
import { Skeleton } from '@/components/ui/skeleton'
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group'
import { useCurrentLibrary } from '@/features/library/composables/useCurrentLibrary'
import { cn } from '@/lib/utils'
import ConfirmDialog from '@/components/app/ConfirmDialog.vue'
import WatchlistRow from '../components/WatchlistRow.vue'
import {
  TRACKING_STATUSES,
  useDeleteTracking,
  useTrackings,
  type TrackingStatus,
} from '../composables/useWatchlist'
import { groupTrackings } from '../lib/groups'

const auth = useAuthStore()
const { t, locale } = useI18n()
const current = useCurrentLibrary()

const scope = ref<'mine' | 'all'>('mine')
const trackings = useTrackings(() => scope.value === 'mine')
const statuses = ref<TrackingStatus[]>([])
const remove = useDeleteTracking()
const deleting = ref<Tracking | null>(null)

const all = computed(() => trackings.data.value ?? [])
const counts = computed(() =>
  Object.fromEntries(
    TRACKING_STATUSES.map((s) => [s, all.value.filter((e) => e.status === s).length]),
  ),
)
const visible = computed(() =>
  statuses.value.length ? all.value.filter((e) => statuses.value.includes(e.status)) : all.value,
)
const groups = computed(() => groupTrackings(visible.value, locale.value))

function onScope(value: unknown) {
  if (value === 'mine' || value === 'all') scope.value = value
}

function toggleStatus(status: TrackingStatus) {
  statuses.value = statuses.value.includes(status)
    ? statuses.value.filter((s) => s !== status)
    : [...statuses.value, status]
}

function groupTitle(kind: string, label: string): string {
  if (kind === 'released') return t('tracking.groups.released')
  if (kind === 'tba') return t('tracking.groups.tba')
  return label
}

async function confirmDelete() {
  const entry = deleting.value
  if (!entry) return
  try {
    await remove.mutateAsync(entry.id)
    deleting.value = null
    toast.success(t('tracking.delete.done'))
  } catch (error) {
    toast.error((error as Error).message)
  }
}
</script>

<template>
  <header class="flex flex-wrap items-center justify-between gap-3 border-b px-4 py-3 md:px-6">
    <div class="min-w-0 flex-1">
      <h1 class="text-lg font-semibold tracking-tight">{{ t('tracking.title') }}</h1>
      <p class="text-sm text-muted-foreground">{{ t('tracking.subtitle') }}</p>
    </div>
  </header>

  <div class="grid gap-6 p-4 md:px-6">
    <!-- One filter row: whose entries, then which status. -->
    <div class="flex flex-wrap items-center gap-1.5" data-testid="filters">
      <ToggleGroup
        type="single"
        variant="outline"
        size="sm"
        class="mr-2"
        :model-value="scope"
        :aria-label="t('tracking.scope.label')"
        data-testid="scope"
        @update:model-value="onScope"
      >
        <ToggleGroupItem value="mine" data-testid="scope-mine">
          {{ t('tracking.scope.mine') }}
        </ToggleGroupItem>
        <ToggleGroupItem value="all" data-testid="scope-all">
          {{ t('tracking.scope.all') }}
        </ToggleGroupItem>
      </ToggleGroup>
      <div
        v-if="all.length"
        class="flex flex-wrap gap-1.5"
        role="group"
        :aria-label="t('tracking.filter')"
      >
        <button
          v-for="s in TRACKING_STATUSES"
          :key="s"
          type="button"
          :aria-pressed="statuses.includes(s)"
          :data-testid="`filter-${s}`"
          :class="
            cn(
              'inline-flex h-7 items-center gap-1.5 rounded-full border px-3 text-xs transition-colors',
              statuses.includes(s)
                ? 'border-foreground bg-foreground text-background'
                : 'bg-background text-muted-foreground hover:bg-muted hover:text-foreground',
            )
          "
          @click="toggleStatus(s)"
        >
          {{ t(`choices.tracking.${s}`) }}
          <span class="font-mono tabular opacity-70">{{ counts[s] }}</span>
        </button>
      </div>
    </div>

    <div v-if="trackings.isPending.value" class="grid gap-1">
      <Skeleton v-for="n in 4" :key="n" class="h-12 rounded-md" />
    </div>
    <p v-else-if="trackings.isError.value" class="text-sm text-destructive" role="alert">
      {{ trackings.error.value?.message }}
    </p>
    <Empty v-else-if="!all.length" class="mx-auto max-w-lg border" data-testid="empty">
      <EmptyHeader>
        <EmptyMedia variant="icon"><CalendarClock /></EmptyMedia>
        <EmptyTitle>{{ t('tracking.emptyTitle') }}</EmptyTitle>
        <EmptyDescription>{{ t('tracking.emptyText') }}</EmptyDescription>
        <EmptyDescription class="flex items-start gap-1.5 text-xs">
          {{ auth.canContribute ? t('tracking.emptyHint') : t('tracking.emptyHintWatch') }}
        </EmptyDescription>
      </EmptyHeader>
    </Empty>
    <p v-else-if="!groups.length" class="text-sm text-muted-foreground" data-testid="no-match">
      {{ t('tracking.noMatch') }}
    </p>

    <section
      v-for="group in groups"
      :key="group.key"
      class="grid gap-2"
      :data-testid="`group-${group.kind}`"
    >
      <h2
        class="flex flex-wrap items-baseline gap-x-2 border-b pb-1.5 font-mono text-[11px] tracking-wider text-muted-foreground uppercase"
      >
        <span :class="group.kind === 'released' ? 'text-success' : 'text-foreground'">
          {{ groupTitle(group.kind, group.label) }}
        </span>
        <span v-if="group.kind === 'year'">{{ t('tracking.groups.year') }}</span>
        <span class="ml-auto tabular">
          {{ t('tracking.count', { n: group.entries.length }, group.entries.length) }}
        </span>
      </h2>
      <ul class="divide-y rounded-lg border bg-card">
        <li v-for="entry in group.entries" :key="entry.id" class="min-w-0">
          <WatchlistRow :entry="entry" :library-id="current.id.value" @delete="deleting = $event" />
        </li>
      </ul>
    </section>
  </div>

  <ConfirmDialog
    :open="!!deleting"
    :title="t('tracking.delete.title')"
    :description="t('tracking.delete.text', { title: deleting?.release.title ?? '' })"
    :busy="remove.isPending.value"
    @update:open="(open) => !open && (deleting = null)"
    @confirm="confirmDelete"
  />
</template>
