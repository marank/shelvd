<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import CoverImage from '@/components/app/CoverImage.vue'
import PlatformBadge from '@/components/app/PlatformBadge.vue'
import type { Candidate, Release } from '@/api/types'
import { usePlatforms } from '@/features/library/composables/useReference'
import { formatReleaseDate } from '@/lib/releaseDate'

const props = defineProps<{ candidate: Candidate }>()
defineEmits<{ select: [] }>()
const { t, locale } = useI18n()
const platforms = usePlatforms()
const platform = computed(
  () =>
    platforms.data.value?.find((p) => p.id === props.candidate.platform_id) ?? {
      name: props.candidate.platform_name || t('common.unknown'),
      short_name: '',
      manufacturer: '',
    },
)
// Precision-aware ("Q3 2026") when the source has a date, else just the year.
const date = computed(
  () =>
    formatReleaseDate(
      {
        release_date: props.candidate.release_date,
        release_date_end: null,
        release_precision: props.candidate.release_precision as Release['release_precision'],
      },
      locale.value,
      t('dates.tba'),
    ) || (props.candidate.year ? String(props.candidate.year) : ''),
)
</script>

<template>
  <button
    type="button"
    data-testid="candidate-row"
    class="flex w-full min-w-0 items-center gap-3 rounded-md px-2 py-1.5 text-left hover:bg-accent focus-visible:bg-accent focus-visible:ring-2 focus-visible:ring-ring/50 focus-visible:outline-none"
    @click="$emit('select')"
  >
    <CoverImage
      fit="box"
      :src="candidate.cover_url || null"
      :title="candidate.title"
      :manufacturer="platform.manufacturer"
      class="w-10 shrink-0"
    />
    <span class="min-w-0 flex-1">
      <span class="block font-medium break-words">{{ candidate.title }}</span>
      <span class="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-muted-foreground">
        <PlatformBadge :platform="platform" />
        <span v-if="date" class="font-mono tabular-nums">{{ date }}</span>
        <span v-if="candidate.publisher" class="truncate">{{ candidate.publisher }}</span>
      </span>
    </span>
  </button>
</template>
