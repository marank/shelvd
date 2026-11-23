<script setup lang="ts">
import UnreviewedBadge from '@/components/app/UnreviewedBadge.vue'
import { useI18n } from 'vue-i18n'
import CoverImage from '@/components/app/CoverImage.vue'
import PlatformBadge from '@/components/app/PlatformBadge.vue'
import ReleaseDate from '@/components/app/ReleaseDate.vue'
import type { Release } from '@/api/types'
import OwnedHint from './OwnedHint.vue'

defineProps<{ release: Release }>()
defineEmits<{ select: [] }>()
const { t } = useI18n()
</script>

<template>
  <button
    type="button"
    data-testid="release-row"
    class="flex w-full min-w-0 items-center gap-3 rounded-md px-2 py-1.5 text-left hover:bg-accent focus-visible:bg-accent focus-visible:ring-2 focus-visible:ring-ring/50 focus-visible:outline-none"
    @click="$emit('select')"
  >
    <CoverImage
      fit="box"
      :src="release.cover_url"
      :title="release.title"
      :manufacturer="release.platform.manufacturer"
      class="w-10 shrink-0"
    />
    <span class="min-w-0 flex-1">
      <span class="block font-medium break-words">{{ release.title }}</span>
      <span class="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-muted-foreground">
        <PlatformBadge :platform="release.platform" />
        <span>{{ t(`choices.region.${release.region}`) }}</span>
        <ReleaseDate :release="release" />
        <span v-if="release.publisher" class="truncate">{{ release.publisher.name }}</span>
        <span v-if="release.edition" class="truncate">{{ release.edition }}</span>
        <UnreviewedBadge
          v-if="release.review_status === 'pending' || release.pending_barcodes.length"
        />
      </span>
      <OwnedHint :release="release" class="mt-1" />
    </span>
  </button>
</template>
