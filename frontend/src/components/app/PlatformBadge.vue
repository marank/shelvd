<script setup lang="ts">
import { computed } from 'vue'
import { platformColor } from '@/lib/labels'
import { PLATFORM_ICONS } from '@/lib/platformIcons'
import type { Platform } from '@/api/types'

const props = defineProps<{
  platform: Pick<Platform, 'name' | 'short_name' | 'manufacturer'> &
    Partial<Pick<Platform, 'color' | 'icon' | 'icon_url' | 'icon_dark'>>
}>()
const color = computed(() => platformColor(props.platform))
/** An uploaded icon wins over a built-in symbol; without either, a coloured dot. */
const symbol = computed(() => PLATFORM_ICONS[props.platform.icon ?? ''])
</script>

<template>
  <span
    class="inline-flex items-center gap-1.5 rounded-sm border bg-background/80 px-1.5 py-0.5 font-mono text-[11px] leading-none font-medium tracking-tight text-foreground/80"
    :title="platform.name"
  >
    <img
      v-if="platform.icon_url"
      :src="platform.icon_url"
      alt=""
      class="size-3 shrink-0 object-contain"
      :class="platform.icon_dark && 'dark:invert'"
      data-testid="platform-icon"
    />
    <component
      :is="symbol"
      v-else-if="symbol"
      class="size-3 shrink-0"
      :style="{ color }"
      aria-hidden="true"
      data-testid="platform-symbol"
    />
    <span v-else class="size-1.5 shrink-0 rounded-full" :style="{ backgroundColor: color }" />
    {{ platform.short_name || platform.name }}
  </span>
</template>
