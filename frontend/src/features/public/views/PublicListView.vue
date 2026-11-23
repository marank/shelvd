<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'
import CoverImage from '@/components/app/CoverImage.vue'
import PlatformBadge from '@/components/app/PlatformBadge.vue'
import ReleaseDate from '@/components/app/ReleaseDate.vue'
import { Skeleton } from '@/components/ui/skeleton'
import LinkGone from '../components/LinkGone.vue'
import { isGone, usePublicList } from '../composables/usePublic'
import SourceLink from '@/components/app/SourceLink.vue'

const { t } = useI18n()
const route = useRoute()
const list = usePublicList(computed(() => String(route.params.token)))
const entries = computed(() =>
  [...(list.data.value?.entries ?? [])].sort((a, b) => a.position - b.position),
)
</script>

<template>
  <LinkGone v-if="isGone(list.error.value)" />
  <div v-else class="mx-auto grid max-w-3xl gap-5">
    <header class="grid gap-1 border-b pb-4">
      <Skeleton v-if="list.isPending.value" class="h-7 w-56" />
      <template v-else-if="list.data.value">
        <h1 class="text-xl font-semibold tracking-tight">{{ list.data.value.name }}</h1>
        <p v-if="list.data.value.description" class="text-sm text-muted-foreground">
          {{ list.data.value.description }}
        </p>
        <p class="font-mono text-[11px] tracking-wider text-muted-foreground uppercase">
          {{ t('public.sharedBy', { owner: list.data.value.owner }) }} ·
          <span class="tabular">{{
            t('common.games', { n: entries.length }, entries.length)
          }}</span>
        </p>
      </template>
      <p v-else class="text-sm text-destructive">{{ list.error.value?.message }}</p>
    </header>

    <p
      v-if="list.data.value && !entries.length"
      class="py-10 text-center text-sm text-muted-foreground"
    >
      {{ t('public.emptyList') }}
    </p>
    <ol v-else class="divide-y">
      <li
        v-for="(entry, index) in entries"
        :key="entry.id"
        class="flex items-start gap-3 py-3"
        data-testid="public-entry"
      >
        <span class="w-5 shrink-0 pt-1 text-right font-mono text-xs text-muted-foreground tabular">
          {{ index + 1 }}
        </span>
        <CoverImage
          fit="box"
          :src="entry.release.cover_url"
          :title="entry.release.title"
          :manufacturer="entry.release.platform.manufacturer"
          class="w-12 shrink-0"
        />
        <div class="grid min-w-0 gap-1">
          <div class="flex flex-wrap items-center gap-x-2 gap-y-1">
            <span class="font-medium">{{ entry.release.title }}</span>
            <PlatformBadge :platform="entry.release.platform" />
            <ReleaseDate
              :release="entry.release"
              class="text-xs text-muted-foreground"
              data-testid="public-entry-date"
            />
          </div>
          <p v-if="entry.note" class="text-sm text-muted-foreground">{{ entry.note }}</p>
        </div>
      </li>
    </ol>
    <SourceLink />
  </div>
</template>
