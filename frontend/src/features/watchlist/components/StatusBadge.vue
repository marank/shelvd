<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { Badge } from '@/components/ui/badge'
import type { TrackingStatus } from '../composables/useWatchlist'

defineProps<{ status: TrackingStatus }>()
const { t } = useI18n()

const tone: Record<TrackingStatus, string> = {
  watching: 'bg-muted text-muted-foreground',
  preordered: 'bg-primary/12 text-primary',
  bought: 'bg-success/15 text-success',
}
</script>

<template>
  <Badge :class="tone[status]" :data-status="status" data-testid="status-badge">
    {{ t(`choices.tracking.${status}`) }}
  </Badge>
</template>
