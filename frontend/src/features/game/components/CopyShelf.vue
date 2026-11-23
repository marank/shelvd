<script setup lang="ts">
// Copies of a game in this library as covers – any number, wrapping; each opens its page.
// The one the page is about is outlined.
import CoverImage from '@/components/app/CoverImage.vue'
import type { Item } from '@/api/types'
import { copyLabel } from '@/features/items/composables/labels'

defineProps<{ copies: Item[]; current?: string }>()
</script>

<template>
  <ul class="grid grid-cols-[repeat(auto-fill,minmax(5.5rem,1fr))] gap-3" data-testid="copy-shelf">
    <li v-for="copy in copies" :key="copy.id">
      <RouterLink
        :to="{ name: 'item', params: { itemId: copy.id } }"
        class="group block"
        data-testid="shelf-copy"
        :data-current="copy.id === current || undefined"
      >
        <CoverImage
          fit="box"
          :src="copy.cover_url"
          :aspect="copy.cover_aspect"
          :title="copy.title"
          :manufacturer="copy.release.platform.manufacturer"
          class="w-full rounded-md ring-offset-2 ring-offset-background transition group-hover:ring-1 group-hover:ring-border"
          :class="
            copy.id === current
              ? 'ring-2 ring-primary group-hover:ring-2 group-hover:ring-primary'
              : ''
          "
        />
        <span class="mt-1.5 block text-xs leading-snug break-words text-muted-foreground">
          {{ copyLabel(copy) }}
        </span>
      </RouterLink>
    </li>
  </ul>
</template>
