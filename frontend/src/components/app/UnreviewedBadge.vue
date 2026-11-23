<script setup lang="ts">
// Entered by hand (or a barcode assigned) and not checked by an admin yet.
import { ShieldQuestion } from '@lucide/vue'
import { useI18n } from 'vue-i18n'
import { Badge } from '@/components/ui/badge'

const { t } = useI18n()
</script>

<template>
  <Badge
    variant="outline"
    class="gap-1 border-warning/50 text-warning"
    :title="t('review.badgeTitle')"
    data-testid="unreviewed"
  >
    <ShieldQuestion class="size-3" /> {{ t('review.badge') }}
  </Badge>
</template>
