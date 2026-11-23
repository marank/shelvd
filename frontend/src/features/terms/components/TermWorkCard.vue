<script setup lang="ts">
import CoverImage from '@/components/app/CoverImage.vue'
import PlatformBadge from '@/components/app/PlatformBadge.vue'
import type { TermWork } from '../composables/useTermPages'

/** A game on a term's page: cover (full width, its own height), first platform, title,
 * year. The text block always has the same height, so in a grid aligned to the bottom
 * the covers of a row stand on one line. */
defineProps<{ work: TermWork }>()
</script>

<template>
  <RouterLink
    :to="{ name: 'work', params: { workId: work.id } }"
    class="group/card flex min-w-0 flex-col gap-2 rounded-lg p-1.5 transition hover:bg-accent/50 focus-visible:ring-[3px] focus-visible:ring-ring/40 focus-visible:outline-none"
    data-testid="term-work"
  >
    <CoverImage
      :src="work.cover_url"
      :aspect="work.cover_aspect"
      :title="work.title"
      :manufacturer="work.manufacturer"
      class="w-full shadow-sm transition group-hover/card:shadow-md"
    >
      <span
        v-if="work.platforms.length"
        class="absolute right-1 bottom-1 left-1 flex gap-1 overflow-hidden whitespace-nowrap"
      >
        <PlatformBadge :platform="work.platforms[0]!" class="shrink-0" />
        <span
          v-if="work.platforms.length > 1"
          class="tabular shrink-0 rounded-sm border bg-background/80 px-1 py-0.5 font-mono text-[11px] leading-none text-foreground/80"
          :title="work.platforms.map((p) => p.name).join(', ')"
          >+{{ work.platforms.length - 1 }}</span
        >
      </span>
    </CoverImage>
    <div class="min-w-0 px-0.5">
      <!-- Two lines for every title: the covers of a row stand on one line. -->
      <p class="line-clamp-2 min-h-[2lh] text-[13px] leading-snug font-medium">
        {{ work.title }}
      </p>
      <p class="tabular truncate font-mono text-[11px] text-muted-foreground">
        {{ work.year ?? '—' }}
      </p>
    </div>
  </RouterLink>
</template>
