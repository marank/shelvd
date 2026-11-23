<script setup lang="ts">
import { computed } from 'vue'
import ToneBox from '@/components/app/ToneBox.vue'

/** A company's, genre's or series' mark at any size: its picture (logo) – inverted or
 * outlined when it would vanish (ToneBox) –, else its initial on a tint picked from its
 * name – the same name, always the same tint. */
const props = defineProps<{
  name: string
  imageUrl: string | null
  /** How the picture reads (`image_tone`). */
  tone?: string
}>()
const initial = computed(() => {
  const letter = props.name.trim().charAt(0).toLocaleUpperCase()
  return /\p{L}|\d/u.test(letter) ? letter : '#'
})
const hue = computed(() => [...props.name].reduce((h, c) => (h * 31 + c.charCodeAt(0)) % 360, 7))
</script>

<template>
  <ToneBox
    :tone="tone"
    class="@container grid grid-cols-1 grid-rows-1 place-items-center overflow-hidden rounded-md border"
    :class="imageUrl && 'spotlight bg-muted/30 p-[12%]'"
    :style="
      imageUrl
        ? undefined
        : {
            backgroundColor: `oklch(0.6 0.09 ${hue} / 0.14)`,
            borderColor: `oklch(0.6 0.09 ${hue} / 0.3)`,
            color: `oklch(0.55 0.12 ${hue})`,
          }
    "
    aria-hidden="true"
  >
    <img
      v-if="imageUrl"
      :src="imageUrl"
      alt=""
      loading="lazy"
      class="max-h-full max-w-full object-contain"
      data-testid="term-mark-image"
    />
    <span v-else class="font-semibold [font-size:clamp(0.75rem,40cqw,3rem)]">{{ initial }}</span>
  </ToneBox>
</template>
