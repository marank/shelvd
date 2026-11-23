<script setup lang="ts">
import type { PublicItem } from '@/api/types'
import CoverImage from '@/components/app/CoverImage.vue'
import PlatformBadge from '@/components/app/PlatformBadge.vue'
import ReleaseDate from '@/components/app/ReleaseDate.vue'

/** Cover, title, platform and release date of one shared copy. */
defineProps<{ item: PublicItem }>()
</script>

<template>
  <figure class="grid min-w-0 gap-1.5" data-testid="public-item">
    <CoverImage
      :aspect="item.cover_aspect"
      :src="item.cover_url"
      :title="item.title"
      :manufacturer="item.release.platform.manufacturer"
    />
    <figcaption class="grid min-w-0 gap-1">
      <span class="line-clamp-2 text-sm leading-snug font-medium">{{ item.title }}</span>
      <span class="flex flex-wrap items-center gap-1.5">
        <PlatformBadge :platform="item.release.platform" />
        <ReleaseDate
          :release="item.release"
          class="text-[11px] text-muted-foreground"
          data-testid="public-item-date"
        />
      </span>
    </figcaption>
  </figure>
</template>
