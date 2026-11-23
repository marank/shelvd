<script setup lang="ts">
import { HandCoins } from '@lucide/vue'
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import CoverImage from '@/components/app/CoverImage.vue'
import PlatformBadge from '@/components/app/PlatformBadge.vue'
import type { Item } from '@/api/types'
import { useFieldValue, type ItemFieldKey } from '@/lib/itemFields'

const props = defineProps<{
  item: Item
  fields: ItemFieldKey[]
  selected?: boolean
  width: number
}>()
const value = useFieldValue()
const meta = computed(() =>
  props.fields
    .map((key) => value(key, props.item))
    .filter(Boolean)
    .join(' · '),
)

/** Width from the justified row layout; the cover keeps its own aspect ratio inside. */
const style = computed(() => ({ width: `${props.width}px` }))
const emit = defineEmits<{ open: [] }>()
const { t } = useI18n()
</script>

<template>
  <button
    type="button"
    data-testid="item-card"
    :style="style"
    :data-item-id="item.id"
    :aria-current="selected || undefined"
    class="group/card flex min-w-0 flex-col gap-2 rounded-lg p-1.5 text-left transition hover:bg-accent/50 focus-visible:ring-[3px] focus-visible:ring-ring/40 focus-visible:outline-none"
    :class="selected && 'bg-accent ring-2 ring-primary/50'"
    @click="emit('open')"
  >
    <div class="relative">
      <CoverImage
        :aspect="item.cover_aspect"
        :src="item.cover_url"
        :title="item.title"
        :manufacturer="item.release.platform.manufacturer"
        class="w-full shadow-sm transition group-hover/card:shadow-md"
      />
      <span class="absolute bottom-1.5 left-1.5">
        <PlatformBadge :platform="item.release.platform" />
      </span>
      <span
        v-if="item.active_loan"
        class="absolute top-1.5 right-1.5 inline-flex items-center gap-1 rounded-sm bg-warning px-1.5 py-0.5 text-[10px] font-semibold text-black/80"
        :title="
          item.active_loan.borrower
            ? t('explorer.lentTo', { name: item.active_loan.borrower.name })
            : t('items.lent')
        "
      >
        <HandCoins class="size-3" /> {{ item.active_loan.borrower?.name ?? t('items.lent') }}
      </span>
      <span
        v-else-if="item.status !== 'owned'"
        class="absolute top-1.5 right-1.5 rounded-sm bg-background/90 px-1.5 py-0.5 text-[10px] font-medium"
      >
        {{ t(`choices.status.${item.status}`) }}
      </span>
    </div>
    <div class="min-w-0 px-0.5">
      <p class="line-clamp-2 text-[13px] leading-snug font-medium">{{ item.title }}</p>
      <p class="truncate font-mono text-[11px] text-muted-foreground">
        {{ meta || '—' }}
      </p>
    </div>
  </button>
</template>
