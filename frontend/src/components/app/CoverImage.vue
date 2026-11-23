<script setup lang="ts">
import { computed, ref } from 'vue'
import { brandColor } from '@/lib/labels'
import { cn } from '@/lib/utils'

/**
 * A cover, never cropped.
 * - fit "natural" (default): the box takes the cover's own aspect ratio (`aspect` =
 *   width / height from the API; unknown → the image's natural height).
 * - fit "box": a fixed square box with the cover fitted inside — for thumbnails in list
 *   rows, so rows stay the same height.
 * Without a cover: initials on a tint of the platform's brand colour (5:7).
 */
const props = defineProps<{
  src?: string | null
  title: string
  manufacturer?: string
  aspect?: number | null
  fit?: 'natural' | 'box'
  /** "height": the class sets the height and the width follows the cover (hero images). */
  sizeBy?: 'width' | 'height'
  class?: string
}>()

const failed = ref(false)
const showImage = computed(() => !!props.src && !failed.value)
const box = computed(() => props.fit === 'box')
const initials = computed(() =>
  props.title
    .split(/\s+/)
    .filter((w) => /^[\p{L}\p{N}]/u.test(w))
    .slice(0, 2)
    .map((w) => w[0]?.toUpperCase())
    .join(''),
)
const tint = computed(() => brandColor(props.manufacturer ?? ''))
const ratio = computed(() => {
  if (box.value) return '1 / 1'
  if (!showImage.value) return '5 / 7'
  return props.aspect ? String(props.aspect) : undefined
})
</script>

<template>
  <div
    :class="
      cn(
        'relative overflow-hidden rounded-md',
        showImage ? (box ? 'bg-muted/50' : 'bg-transparent') : 'bg-muted',
        !showImage && 'ring-1 ring-foreground/5',
        props.class,
      )
    "
    :style="ratio ? { aspectRatio: ratio } : undefined"
    data-testid="cover"
  >
    <img
      v-if="showImage"
      :src="src ?? undefined"
      :alt="title"
      loading="lazy"
      decoding="async"
      :class="
        ratio
          ? 'size-full object-contain'
          : sizeBy === 'height'
            ? 'block h-full w-auto'
            : 'block h-auto w-full'
      "
      @error="failed = true"
    />
    <div
      v-else
      data-testid="cover-placeholder"
      class="flex size-full items-center justify-center font-mono text-2xl font-semibold tracking-tight text-foreground/50"
      :class="box && 'text-xs'"
      :style="{
        background: `linear-gradient(145deg, color-mix(in oklch, ${tint} 22%, transparent), color-mix(in oklch, ${tint} 6%, transparent))`,
      }"
    >
      {{ initials }}
    </div>
    <!-- Overlays (platform, status …) sit on the cover itself, whatever its shape. -->
    <slot />
  </div>
</template>
