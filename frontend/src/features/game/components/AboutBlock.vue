<script setup lang="ts">
// One thing the game is connected to, under its cover – its series, a company: always its
// name, and its logo or picture beside it, as high as label and name together. Linked to
// its page.
import type { RouteLocationRaw } from 'vue-router'
import ToneBox from '@/components/app/ToneBox.vue'

defineProps<{
  label: string
  name: string
  to: RouteLocationRaw
  image?: string | null
  /** How the picture reads (`image_tone`). */
  tone?: string
}>()
</script>

<template>
  <!-- At least 56 px high, so a logo has room; the text sits in the middle. -->
  <RouterLink :to="to" class="group flex min-h-14 items-stretch gap-3" data-testid="about-block">
    <div class="flex min-w-0 flex-1 flex-col justify-center space-y-1">
      <p class="font-mono text-[11px] tracking-wider text-muted-foreground uppercase">
        {{ label }}
      </p>
      <p class="text-sm font-semibold break-words group-hover:underline">{{ name }}</p>
    </div>
    <!-- The logo takes the block's height, whatever its shape (wide or square). -->
    <ToneBox v-if="image" :tone="tone" class="relative w-2/5 shrink-0 rounded-md">
      <img
        :src="image"
        alt=""
        class="absolute inset-0 size-full object-contain object-right p-1"
        data-testid="about-image"
      />
    </ToneBox>
  </RouterLink>
</template>
