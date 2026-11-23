<script setup lang="ts">
import { useUiStore, type AddDestination } from '@/stores/ui'
import { ArrowLeft, BookmarkPlus, Check, ChevronRight, Library, ScanBarcode } from '@lucide/vue'
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import CoverImage from '@/components/app/CoverImage.vue'
import ReleaseMeta from '@/components/app/ReleaseMeta.vue'
import ReleaseDate from '@/components/app/ReleaseDate.vue'
import type { Item, Release, Tracking } from '@/api/types'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible'
import { Spinner } from '@/components/ui/spinner'
import {
  TRACKING_STATUSES,
  useCreateTracking,
  type TrackingStatus,
} from '@/features/watchlist/composables/useWatchlist'
import { cn } from '@/lib/utils'
import { useCreateItem } from '../composables/useAddApi'
import { toItemIn, type ItemDetails } from '../composables/useItemDetails'
import NativeSelect from '@/components/app/NativeSelect.vue'
import ItemDetailsFields from './ItemDetailsFields.vue'
import OwnedHint from './OwnedHint.vue'

const props = defineProps<{ release: Release; libraryId: string }>()
const emit = defineEmits<{
  created: [item: Item, next: boolean]
  tracked: [entry: Tracking]
  back: []
}>()
const details = defineModel<ItemDetails>('details', { required: true })
const open = defineModel<boolean>('open', { default: false })
const { t } = useI18n()
const create = useCreateItem(() => props.libraryId)
const tracker = useCreateTracking()

/** Into the library now, or onto Upcoming: as the dialog was opened for (from Upcoming),
 * else by whether the game is out yet. */
const ui = useUiStore()
const destination = ref<AddDestination>(
  ui.addDestination ?? (props.release.is_released ? 'library' : 'track'),
)
const trackStatus = ref<TrackingStatus>('watching')
const pending = computed(() => create.isPending.value || tracker.isPending.value)
const error = computed(() =>
  destination.value === 'track' ? tracker.error.value : create.error.value,
)

const DESTINATIONS = [
  { value: 'library', icon: Library },
  { value: 'track', icon: BookmarkPlus },
] as const

function submit(next: boolean) {
  if (pending.value) return
  if (destination.value === 'track') {
    tracker.mutate(
      {
        release_id: props.release.id,
        status: trackStatus.value,
        library_id: props.libraryId || null,
      },
      { onSuccess: (entry) => emit('tracked', entry) },
    )
    return
  }
  create.mutate(toItemIn(props.release.id, details.value), {
    onSuccess: (item) => emit('created', item, next),
  })
}
</script>

<template>
  <form class="grid grid-cols-1 gap-4" data-testid="item-form" @submit.prevent="submit(false)">
    <div class="flex items-center gap-3 rounded-lg border bg-card p-2" data-testid="chosen-release">
      <CoverImage
        fit="box"
        :src="release.cover_url"
        :title="release.title"
        :manufacturer="release.platform.manufacturer"
        class="w-12 shrink-0"
      />
      <div class="min-w-0 flex-1">
        <p class="font-medium break-words">{{ release.title }}</p>
        <ReleaseMeta :release="release" />
        <OwnedHint :release="release" class="mt-1" />
      </div>
      <ReleaseDate :release="release" hint class="shrink-0 text-right text-xs" />
    </div>

    <div
      class="grid grid-cols-1 gap-2 sm:grid-cols-2"
      role="radiogroup"
      :aria-label="t('add.destination.label')"
      data-testid="destination"
    >
      <label
        v-for="d in DESTINATIONS"
        :key="d.value"
        :class="
          cn(
            'flex cursor-pointer gap-2.5 rounded-lg border p-3 text-sm transition-colors has-focus-visible:ring-3 has-focus-visible:ring-ring/50',
            destination === d.value ? 'border-primary bg-primary/5' : 'hover:bg-muted/50',
          )
        "
      >
        <input
          v-model="destination"
          type="radio"
          name="destination"
          class="mt-0.5 accent-primary"
          :value="d.value"
          :data-testid="`destination-${d.value}`"
        />
        <span class="grid gap-0.5">
          <span class="flex items-center gap-1.5 font-medium">
            <component :is="d.icon" class="size-4 text-muted-foreground" />
            {{ t(`add.destination.${d.value}`) }}
          </span>
          <span class="text-xs text-muted-foreground">
            {{ t(`add.destination.${d.value}Text`) }}
          </span>
        </span>
      </label>
    </div>

    <div v-if="destination === 'track'" class="grid gap-1.5 sm:max-w-xs">
      <label for="track-status" class="text-sm font-medium">{{ t('fields.status') }}</label>
      <NativeSelect id="track-status" v-model="trackStatus">
        <option v-for="s in TRACKING_STATUSES" :key="s" :value="s">
          {{ t(`choices.tracking.${s}`) }}
        </option>
      </NativeSelect>
    </div>

    <Collapsible v-if="destination === 'library'" v-model:open="open">
      <CollapsibleTrigger as-child>
        <Button type="button" variant="ghost" size="sm" class="-ml-2" data-testid="more-details">
          <ChevronRight class="size-4 transition-transform" :class="{ 'rotate-90': open }" />
          {{ t('add.details.more') }}
        </Button>
      </CollapsibleTrigger>
      <CollapsibleContent>
        <ItemDetailsFields
          v-model:details="details"
          :library-id="libraryId"
          per-copy
          class="pt-2"
        />
      </CollapsibleContent>
    </Collapsible>

    <Alert v-if="error" variant="destructive" data-testid="item-error">
      <AlertDescription>{{ error.message }}</AlertDescription>
    </Alert>

    <div class="flex flex-col-reverse gap-2 sm:flex-row sm:items-center sm:justify-between">
      <Button type="button" variant="ghost" @click="emit('back')">
        <ArrowLeft class="size-4" />
        {{ t('actions.back') }}
      </Button>
      <Button
        v-if="destination === 'track'"
        type="submit"
        :disabled="pending"
        data-testid="track-item"
      >
        <Spinner v-if="pending" />
        <BookmarkPlus v-else class="size-4" />
        {{ t('add.track.submit') }}
      </Button>
      <div v-else class="flex flex-col-reverse gap-2 sm:flex-row">
        <Button
          type="button"
          variant="outline"
          :disabled="create.isPending.value"
          data-testid="add-next"
          @click="submit(true)"
        >
          <ScanBarcode class="size-4" />
          {{ t('add.details.addAndScan') }}
        </Button>
        <Button type="submit" :disabled="create.isPending.value" data-testid="add-item">
          <Spinner v-if="create.isPending.value" />
          <Check v-else class="size-4" />
          {{ t('add.details.add') }}
        </Button>
      </div>
    </div>
  </form>
</template>
