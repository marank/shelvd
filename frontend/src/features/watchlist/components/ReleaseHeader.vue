<script setup lang="ts">
import CoverImage from '@/components/app/CoverImage.vue'
import ReleaseMeta from '@/components/app/ReleaseMeta.vue'
import ReleaseDate from '@/components/app/ReleaseDate.vue'
import type { Release } from '@/api/types'

/** The release an edit page is about: cover, title, platform and date (+ actions slot). */
defineProps<{ release: Release }>()
</script>

<template>
  <div class="flex items-center gap-4 py-6" data-testid="release-header">
    <CoverImage
      :aspect="release.cover_aspect"
      :src="release.cover_url"
      :title="release.title"
      :manufacturer="release.platform.manufacturer"
      class="w-16 shrink-0 sm:w-20"
    />
    <div class="min-w-0 flex-1">
      <p class="font-medium">{{ release.title }}</p>
      <ReleaseMeta :release="release" />
      <div class="mt-2 text-sm">
        <ReleaseDate :release="release" hint />
      </div>
      <!-- Actions about the game itself, e.g. "View game". -->
      <div v-if="$slots.default" class="mt-3 flex flex-wrap gap-2">
        <slot />
      </div>
    </div>
  </div>
</template>
