<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import PlatformBadge from '@/components/app/PlatformBadge.vue'
import type { Release } from '@/api/types'

/** The line under a release's title: platform, region and edition. */
defineProps<{ release: Pick<Release, 'platform' | 'region' | 'edition'> }>()
const { t } = useI18n()
</script>

<template>
  <p class="mt-1 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
    <PlatformBadge :platform="release.platform" />
    <span>{{ t(`choices.region.${release.region}`) }}</span>
    <span v-if="release.edition">{{ release.edition }}</span>
  </p>
</template>
