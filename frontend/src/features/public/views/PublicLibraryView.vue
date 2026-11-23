<script setup lang="ts">
import { Search } from '@lucide/vue'
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'
import { PUBLIC_GROUP_FIELDS, type GroupField } from '@/api/types'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Skeleton } from '@/components/ui/skeleton'
import { Spinner } from '@/components/ui/spinner'
import { useFieldLabel } from '@/lib/itemFields'
import { useGroupLabel } from '@/lib/labels'
import { cn } from '@/lib/utils'
import LinkGone from '../components/LinkGone.vue'
import PublicItemCard from '../components/PublicItemCard.vue'
import { isGone, usePublicItems, usePublicLibrary, usePublicTree } from '../composables/usePublic'
import SourceLink from '@/components/app/SourceLink.vue'

const { t } = useI18n()
const route = useRoute()
const groupLabel = useGroupLabel()
const fieldLabel = useFieldLabel()
const token = computed(() => String(route.params.token))

const groupBy = ref<GroupField>('platform.name')
const selected = ref<string | null>(null)
const q = ref('')
watch(groupBy, () => (selected.value = null))

const filters = computed(() => (selected.value ? [`${groupBy.value}:${selected.value}`] : []))
const library = usePublicLibrary(token)
const tree = usePublicTree(token, groupBy)
const items = usePublicItems(token, filters)

const gone = computed(() => isGone(library.error.value) || isGone(items.error.value))
const loaded = computed(() => items.data.value?.pages.flatMap((p) => p.items) ?? [])
const total = computed(() => items.data.value?.pages[0]?.count ?? 0)
const shown = computed(() => {
  const needle = q.value.trim().toLowerCase()
  if (!needle) return loaded.value
  return loaded.value.filter((i) => i.title.toLowerCase().includes(needle))
})

function chip(active: boolean) {
  return cn(
    'inline-flex shrink-0 items-center gap-1.5 rounded-md border px-2.5 py-1 text-sm transition-colors',
    active ? 'border-foreground/30 bg-muted font-medium' : 'bg-card hover:bg-muted/60',
  )
}
</script>

<template>
  <LinkGone v-if="gone" />
  <div v-else class="grid gap-5">
    <header class="grid gap-1 border-b pb-4">
      <Skeleton v-if="library.isPending.value" class="h-7 w-56" />
      <template v-else-if="library.data.value">
        <h1 class="text-xl font-semibold tracking-tight">{{ library.data.value.name }}</h1>
        <p v-if="library.data.value.description" class="text-sm text-muted-foreground">
          {{ library.data.value.description }}
        </p>
        <p class="font-mono text-[11px] tracking-wider text-muted-foreground uppercase">
          {{ t('public.sharedBy', { owner: library.data.value.owner }) }} ·
          <span class="tabular">
            {{
              t('common.games', { n: library.data.value.item_count }, library.data.value.item_count)
            }}
          </span>
        </p>
      </template>
      <p v-else class="text-sm text-destructive">{{ library.error.value?.message }}</p>
    </header>

    <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
      <div class="flex items-center gap-2">
        <label
          for="public-group-by"
          class="font-mono text-[11px] tracking-wider text-muted-foreground uppercase"
        >
          {{ t('public.groupBy') }}
        </label>
        <!-- eslint-disable-next-line vuejs-accessibility/form-control-has-label -- the root only holds the value; the trigger carries the id the label points to -->
        <Select v-model="groupBy">
          <SelectTrigger id="public-group-by" data-testid="group-by" class="min-w-40">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem v-for="field in PUBLIC_GROUP_FIELDS" :key="field" :value="field">
              {{ fieldLabel(field) }}
            </SelectItem>
          </SelectContent>
        </Select>
      </div>
      <div class="relative sm:w-64">
        <Search
          class="pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-muted-foreground"
        />
        <Input
          v-model="q"
          data-testid="title-filter"
          class="pl-8"
          :placeholder="t('public.filterPlaceholder')"
          :aria-label="t('public.filterPlaceholder')"
        />
      </div>
    </div>

    <nav class="-mx-4 flex gap-2 overflow-x-auto px-4 pb-1" data-testid="folders">
      <button type="button" :class="chip(selected === null)" @click="selected = null">
        {{ t('public.all') }}
        <span class="font-mono text-xs text-muted-foreground tabular">{{
          tree.data.value?.total ?? ''
        }}</span>
      </button>
      <button
        v-for="node in tree.data.value?.nodes ?? []"
        :key="node.key"
        type="button"
        data-testid="folder"
        :aria-pressed="selected === node.key"
        :class="chip(selected === node.key)"
        @click="selected = node.key"
      >
        {{ groupLabel(node.field, node.key, node.label) }}
        <span class="font-mono text-xs text-muted-foreground tabular">{{ node.count }}</span>
      </button>
    </nav>

    <div v-if="items.isPending.value" class="flex justify-center py-10">
      <Spinner class="size-6" />
    </div>
    <p v-else-if="items.isError.value" class="text-sm text-destructive">
      {{ items.error.value?.message }}
    </p>
    <p v-else-if="!loaded.length" class="py-10 text-center text-sm text-muted-foreground">
      {{ t('public.noItems') }}
    </p>
    <p v-else-if="!shown.length" class="py-10 text-center text-sm text-muted-foreground">
      {{ t('public.noMatches', { q: q.trim() }) }}
    </p>
    <ul
      v-else
      class="grid grid-cols-3 gap-x-3 gap-y-5 sm:grid-cols-4 md:grid-cols-5 lg:grid-cols-6"
    >
      <li v-for="item in shown" :key="item.id">
        <PublicItemCard :item="item" />
      </li>
    </ul>

    <div v-if="loaded.length" class="flex flex-col items-center gap-2">
      <span class="font-mono text-[11px] text-muted-foreground tabular" data-testid="showing">
        {{ t('public.showing', { shown: loaded.length, total }) }}
      </span>
      <Button
        v-if="items.hasNextPage.value"
        variant="outline"
        data-testid="load-more"
        :disabled="items.isFetchingNextPage.value"
        @click="items.fetchNextPage()"
      >
        {{ t('actions.loadMore') }}
      </Button>
    </div>
    <SourceLink />
  </div>
</template>
