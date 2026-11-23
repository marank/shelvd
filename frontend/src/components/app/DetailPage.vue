<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import type { RouteLocationRaw } from 'vue-router'
import BackButton from '@/components/app/BackButton.vue'
import LevelTrail from '@/components/app/LevelTrail.vue'
import { Skeleton } from '@/components/ui/skeleton'
import type { FieldLevel } from '@/lib/itemFields'

/** The frame of the game, release and copy pages: back, the level trail, then the page –
 * or a skeleton while loading, or "not found". Same width, spacing and states for all. */
defineProps<{
  libraryId: string
  /** The level trail; the copy page goes without (its levels are links further down). */
  trail?: { level: FieldLevel; label: string; to?: RouteLocationRaw }[]
  loaded: boolean
  error?: boolean
}>()
const { t } = useI18n()
</script>

<template>
  <div class="flex-1 overflow-y-auto">
    <div class="@container mx-auto max-w-5xl space-y-6 px-4 py-4 md:px-6 md:py-6">
      <BackButton :library-id="libraryId" data-testid="page-back" />
      <template v-if="loaded">
        <LevelTrail v-if="trail?.length" :steps="trail" />
        <div class="space-y-8">
          <slot />
        </div>
      </template>
      <div v-else-if="error" class="py-16 text-center text-muted-foreground">
        {{ t('errors.notFound') }}
      </div>
      <div v-else class="flex flex-col gap-5 @lg:flex-row" data-testid="page-pending">
        <Skeleton class="mx-auto aspect-[5/7] h-80 @lg:mx-0 @lg:h-64 @3xl:h-80" />
        <div class="flex-1 space-y-3">
          <Skeleton class="h-8 w-2/3" />
          <Skeleton class="h-5 w-1/3" />
          <Skeleton class="h-20 w-full" />
        </div>
      </div>
    </div>
  </div>
</template>
