<script setup lang="ts">
import { Globe, ListChecks, Plus } from '@lucide/vue'
import { useI18n } from 'vue-i18n'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Empty,
  EmptyContent,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from '@/components/ui/empty'
import { Skeleton } from '@/components/ui/skeleton'
import { useLists } from '../composables/useLists'

const { t } = useI18n()
const lists = useLists()
</script>

<template>
  <header class="flex flex-wrap items-center justify-between gap-3 border-b px-4 py-3 md:px-6">
    <div class="min-w-0">
      <h1 class="text-lg font-semibold tracking-tight">{{ t('lists.title') }}</h1>
      <p class="text-sm text-muted-foreground">{{ t('lists.subtitle') }}</p>
    </div>
    <Button as-child>
      <RouterLink :to="{ name: 'list-new' }" data-testid="new-list">
        <Plus />
        {{ t('lists.newList') }}
      </RouterLink>
    </Button>
  </header>

  <div class="p-4 md:px-6">
    <div v-if="lists.isPending.value" class="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
      <Skeleton v-for="n in 3" :key="n" class="h-24 rounded-lg" />
    </div>
    <p v-else-if="lists.isError.value" class="text-sm text-destructive">
      {{ lists.error.value?.message }}
    </p>
    <Empty v-else-if="!lists.data.value?.length" class="mx-auto max-w-lg border">
      <EmptyHeader>
        <EmptyMedia variant="icon"><ListChecks /></EmptyMedia>
        <EmptyTitle>{{ t('lists.emptyTitle') }}</EmptyTitle>
        <EmptyDescription>{{ t('lists.emptyText') }}</EmptyDescription>
      </EmptyHeader>
      <EmptyContent>
        <Button as-child variant="outline">
          <RouterLink :to="{ name: 'list-new' }" data-testid="new-list-empty">
            <Plus />
            {{ t('lists.newList') }}
          </RouterLink>
        </Button>
      </EmptyContent>
    </Empty>
    <ul v-else class="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
      <li v-for="list in lists.data.value" :key="list.id">
        <RouterLink
          :to="{ name: 'list-detail', params: { listId: list.id } }"
          data-testid="list-card"
          class="flex h-full flex-col gap-1.5 rounded-lg border bg-card p-4 transition-colors hover:bg-muted/50 focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:outline-none"
        >
          <div class="flex items-start justify-between gap-2">
            <span class="min-w-0 truncate font-medium">{{ list.name }}</span>
            <Badge v-if="list.public_token" variant="secondary" data-testid="public-badge">
              <Globe />
              {{ t('lists.public') }}
            </Badge>
          </div>
          <p v-if="list.description" class="line-clamp-2 text-sm text-muted-foreground">
            {{ list.description }}
          </p>
          <span
            class="mt-auto pt-1 font-mono text-[11px] tracking-wider text-muted-foreground uppercase tabular"
          >
            {{ t('lists.entries', { n: list.entry_count }, list.entry_count) }}
          </span>
        </RouterLink>
      </li>
    </ul>
  </div>
</template>
