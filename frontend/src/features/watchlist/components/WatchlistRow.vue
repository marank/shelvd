<script setup lang="ts">
import {
  CalendarClock,
  EllipsisVertical,
  ExternalLink,
  PackageCheck,
  Pencil,
  Trash2,
} from '@lucide/vue'
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'
import { toast } from 'vue-sonner'
import CoverImage from '@/components/app/CoverImage.vue'
import PlatformBadge from '@/components/app/PlatformBadge.vue'
import type { Tracking } from '@/api/types'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { formatReleaseDate, relativeHint } from '@/lib/releaseDate'
import {
  TRACKING_STATUSES,
  useUpdateTracking,
  type TrackingStatus,
} from '../composables/useWatchlist'
import { formatPrice } from '../lib/format'
import StatusBadge from './StatusBadge.vue'

/** One entry on Upcoming: the whole row opens it; everything else is in one menu. */
const props = defineProps<{
  entry: Tracking
  /** The library you're in: "View game" opens the game there (never switches library). */
  libraryId?: string
}>()
const emit = defineEmits<{ delete: [entry: Tracking] }>()
const { t, locale } = useI18n()
const route = useRoute()
const update = useUpdateTracking()

const release = computed(() => props.entry.release)
const date = computed(() => formatReleaseDate(release.value, locale.value, t('dates.tba')))
const hint = computed(() => relativeHint(release.value, locale.value))
const price = computed(() => formatPrice(props.entry.price, locale.value))
const purchase = computed(() => [props.entry.shop, price.value].filter(Boolean).join(' · '))
const open = computed(() => ({ name: 'tracking-edit', params: { trackingId: props.entry.id } }))
const workLink = computed(() =>
  props.libraryId ? { name: 'work', params: { workId: release.value.work_id } } : null,
)
const dateLink = computed(() => ({
  name: 'release-edit',
  params: { releaseId: release.value.id },
  query: { back: route.fullPath },
}))

function setStatus(value: unknown) {
  const status = value as TrackingStatus
  if (status === props.entry.status) return
  update.mutate(
    { id: props.entry.id, body: { status } },
    {
      onSuccess: () =>
        toast.success(t('tracking.statusChanged', { status: t(`choices.tracking.${status}`) })),
      onError: (error) => toast.error(error.message),
    },
  )
}
</script>

<template>
  <!-- One compact row: date | cover | title + facts | actions. The title link covers the
       whole row; the actions sit above it. Wraps on phones. -->
  <article
    data-testid="tracking-card"
    :data-id="entry.id"
    class="relative flex flex-wrap items-center gap-x-3 gap-y-2 px-3 py-2 hover:bg-accent/40 sm:flex-nowrap"
  >
    <div
      class="hidden w-24 shrink-0 font-mono text-xs tabular sm:block"
      data-testid="tracking-date"
    >
      <p class="font-semibold">{{ date }}</p>
      <p v-if="hint" class="text-[11px] text-muted-foreground">{{ hint }}</p>
    </div>
    <CoverImage
      fit="box"
      :src="release.cover_url"
      :title="release.title"
      :manufacturer="release.platform.manufacturer"
      class="w-8 shrink-0 rounded-sm text-[10px]"
    />
    <div class="min-w-0 flex-1">
      <p class="font-mono text-[11px] text-muted-foreground tabular sm:hidden">
        <span class="font-semibold text-foreground">{{ date }}</span>
        <template v-if="hint"> · {{ hint }}</template>
      </p>
      <RouterLink
        :to="open"
        class="block truncate text-sm font-medium after:absolute after:inset-0 focus-visible:outline-none after:focus-visible:ring-2 after:focus-visible:ring-ring/50"
        data-testid="open-entry"
      >
        {{ release.title }}
      </RouterLink>
      <div
        class="flex min-w-0 flex-wrap items-center gap-x-2 gap-y-0.5 text-xs text-muted-foreground"
      >
        <PlatformBadge :platform="release.platform" />
        <span class="font-mono text-[11px] uppercase">{{ release.region }}</span>
        <StatusBadge :status="entry.status" />
        <span v-if="purchase" class="truncate" data-testid="purchase">{{ purchase }}</span>
        <span v-if="!entry.is_mine" class="truncate" data-testid="owner">
          {{ t('tracking.by', { user: entry.user }) }}
        </span>
        <span v-if="entry.library" class="truncate" data-testid="library">
          {{ t('tracking.for', { library: entry.library.name }) }}
        </span>
        <span
          v-if="entry.owned_in.length"
          class="inline-flex items-center gap-1 truncate text-foreground"
          data-testid="owned-in"
        >
          <PackageCheck class="size-3.5 text-primary" />
          {{ t('tracking.ownedIn', { library: entry.owned_in.map((l) => l.name).join(', ') }) }}
        </span>
      </div>
    </div>

    <div class="relative z-10 flex shrink-0 items-center gap-1 sm:ml-auto">
      <Button
        v-if="entry.is_mine && release.is_released && !entry.owned_in.length"
        as-child
        size="sm"
        data-testid="take-over"
      >
        <RouterLink :to="{ name: 'take-over', params: { trackingId: entry.id } }">
          <PackageCheck />
          <span class="hidden md:inline">{{ t('tracking.takeOver') }}</span>
        </RouterLink>
      </Button>
      <DropdownMenu>
        <DropdownMenuTrigger as-child>
          <Button
            variant="ghost"
            size="icon-sm"
            :aria-label="t('tracking.actions', { title: release.title })"
            data-testid="entry-menu"
          >
            <EllipsisVertical class="size-4" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" class="w-60">
          <template v-if="entry.is_mine">
            <DropdownMenuLabel class="text-xs text-muted-foreground">
              {{ t('fields.status') }}
            </DropdownMenuLabel>
            <DropdownMenuRadioGroup :model-value="entry.status" @update:model-value="setStatus">
              <DropdownMenuRadioItem
                v-for="s in TRACKING_STATUSES"
                :key="s"
                :value="s"
                :data-testid="`set-${s}`"
              >
                {{ t(`choices.tracking.${s}`) }}
              </DropdownMenuRadioItem>
            </DropdownMenuRadioGroup>
            <DropdownMenuSeparator />
          </template>
          <DropdownMenuItem as-child>
            <RouterLink :to="open" data-testid="edit">
              <Pencil class="size-4" /> {{ t('tracking.open') }}
            </RouterLink>
          </DropdownMenuItem>
          <DropdownMenuItem v-if="entry.release.can_edit" as-child>
            <RouterLink :to="dateLink" data-testid="change-date">
              <CalendarClock class="size-4" /> {{ t('tracking.changeDate') }}
            </RouterLink>
          </DropdownMenuItem>
          <DropdownMenuItem v-if="workLink" as-child>
            <RouterLink :to="workLink" data-testid="work-link">
              <ExternalLink class="size-4" /> {{ t('tracking.viewGame') }}
            </RouterLink>
          </DropdownMenuItem>
          <template v-if="entry.is_mine">
            <DropdownMenuSeparator />
            <DropdownMenuItem
              variant="destructive"
              data-testid="delete"
              @select="emit('delete', entry)"
            >
              <Trash2 class="size-4" /> {{ t('tracking.button.stop') }}
            </DropdownMenuItem>
          </template>
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  </article>
</template>
