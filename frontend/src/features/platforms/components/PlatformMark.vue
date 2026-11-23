<script setup lang="ts">
import { computed } from 'vue'
import { platformColor } from '@/lib/labels'
import { PLATFORM_ICONS } from '@/lib/platformIcons'
import type { Platform } from '@/api/types'

/** A platform's mark at any size: its icon (small logo; a dark mark is inverted on dark
 * backgrounds), else its symbol in its colour, else a dot – on a soft tile of that colour. */
const props = defineProps<{
  platform: Pick<Platform, 'manufacturer' | 'color' | 'icon' | 'icon_url'> &
    Partial<Pick<Platform, 'icon_dark'>>
}>()
const color = computed(() => platformColor(props.platform))
const symbol = computed(() => PLATFORM_ICONS[props.platform.icon])
</script>

<template>
  <span
    class="grid grid-cols-1 grid-rows-1 place-items-center rounded-md border"
    :style="{
      backgroundColor: `color-mix(in oklab, ${color} 10%, transparent)`,
      borderColor: `color-mix(in oklab, ${color} 25%, transparent)`,
    }"
    aria-hidden="true"
  >
    <img
      v-if="platform.icon_url"
      :src="platform.icon_url"
      alt=""
      class="size-3/5 object-contain"
      :class="platform.icon_dark && 'dark:invert'"
      data-testid="platform-mark-icon"
    />
    <component :is="symbol" v-else-if="symbol" class="size-1/2" :style="{ color }" />
    <span v-else class="size-1/4 rounded-full" :style="{ backgroundColor: color }" />
  </span>
</template>
