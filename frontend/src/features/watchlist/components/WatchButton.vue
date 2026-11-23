<script setup lang="ts">
import { BookmarkCheck, BookmarkPlus } from '@lucide/vue'
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import { toast } from 'vue-sonner'
import { Button } from '@/components/ui/button'
import { Spinner } from '@/components/ui/spinner'
import { cn } from '@/lib/utils'
import { useCreateTracking, useMyTrackings, type TrackingStatus } from '../composables/useWatchlist'

/** On the game page, per release: "Watch" puts it on Upcoming; once there, a chip that
 * opens the entry – status, date and purchase are changed in one place, there. */
const props = defineProps<{ releaseId: string }>()
const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const mine = useMyTrackings()
const create = useCreateTracking()

const entry = computed(() => mine.data.value?.find((e) => e.release.id === props.releaseId))
const openEntry = (id: string) => ({
  name: 'tracking-edit',
  params: { trackingId: id },
  query: { back: route.fullPath },
})

const tone: Record<TrackingStatus, string> = {
  watching: 'text-muted-foreground',
  preordered: 'border-primary/40 text-primary',
  bought: 'border-success/40 text-success',
}

function watchRelease() {
  // No library unless the user picks one on the entry: Upcoming isn't tied to a library.
  create.mutate(
    { release_id: props.releaseId, status: 'watching', library_id: null },
    {
      onSuccess: (created) =>
        toast.success(t('tracking.edit.created', { title: created.release.title }), {
          action: {
            label: t('tracking.button.details'),
            onClick: () => void router.push(openEntry(created.id)),
          },
        }),
      onError: (error) => toast.error(error.message),
    },
  )
}
</script>

<template>
  <Button
    v-if="!entry"
    variant="outline"
    size="sm"
    data-testid="track-button"
    :disabled="mine.isPending.value || create.isPending.value"
    @click="watchRelease"
  >
    <Spinner v-if="create.isPending.value" />
    <BookmarkPlus v-else />
    {{ t('tracking.button.track') }}
  </Button>
  <Button
    v-else
    as-child
    variant="outline"
    size="sm"
    :class="cn(tone[entry.status])"
    data-testid="track-chip"
  >
    <RouterLink
      :to="openEntry(entry.id)"
      :aria-label="t('tracking.button.menu', { status: t(`choices.tracking.${entry.status}`) })"
    >
      <BookmarkCheck />
      {{ t(`choices.tracking.${entry.status}`) }}
    </RouterLink>
  </Button>
</template>
