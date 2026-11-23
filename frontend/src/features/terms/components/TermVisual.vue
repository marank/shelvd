<script setup lang="ts">
import { computed } from 'vue'
import CoverImage from '@/components/app/CoverImage.vue'
import ToneBox from '@/components/app/ToneBox.vue'
import { KIND_ICONS, type TermKind } from '@/lib/terms'
import type { TermWork } from '../composables/useTermPages'

/** The picture at the top of a term's or platform's page: its own image (logo …), else a fan of its
 * games' covers, else its kind's symbol. */
const props = defineProps<{
  kind: TermKind | 'platforms'
  name: string
  imageUrl: string | null
  /** How the picture reads (`image_tone` / `photo_tone`). */
  tone?: string
  /** The picture is a photo (a platform's device): never inverted. */
  photo?: boolean
  works: TermWork[]
}>()
const covers = computed(() => props.works.filter((w) => w.cover_url).slice(-3))
/** Fanned out from the middle: rotation and offset per position. */
const FAN = [
  'left-0 top-3 -rotate-8',
  'right-0 top-3 rotate-8',
  'left-1/2 top-0 -translate-x-1/2 z-10',
]
</script>

<template>
  <ToneBox
    v-if="imageUrl"
    :tone="tone"
    :photo="photo"
    class="spotlight grid grid-cols-1 grid-rows-1 size-40 shrink-0 place-items-center self-center rounded-xl border bg-card p-5 shadow-sm @lg:size-48 @lg:self-start"
    data-testid="term-image"
  >
    <img :src="imageUrl" :alt="name" class="max-h-full max-w-full object-contain" />
  </ToneBox>
  <div
    v-else-if="covers.length"
    class="relative h-44 w-52 shrink-0 self-center @lg:h-52 @lg:w-60 @lg:self-start"
    data-testid="term-covers"
    aria-hidden="true"
  >
    <CoverImage
      v-for="(work, i) in covers"
      :key="work.id"
      :src="work.cover_url"
      :aspect="work.cover_aspect"
      :title="work.title"
      size-by="height"
      :class="`absolute h-36 max-w-32 shadow-lg ring-1 ring-black/5 @lg:h-44 @lg:max-w-36 ${FAN[covers.length === 1 ? 2 : i]}`"
    />
  </div>
  <div
    v-else
    class="grid size-40 shrink-0 place-items-center self-center rounded-xl border border-dashed bg-muted/40 @lg:size-48 @lg:self-start"
  >
    <component :is="KIND_ICONS[kind]" class="size-12 text-muted-foreground/60" />
  </div>
</template>
