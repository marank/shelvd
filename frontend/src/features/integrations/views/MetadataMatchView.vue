<script setup lang="ts">
import { ArrowLeft, RefreshCw, Search } from '@lucide/vue'
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group'
import { useMetadataCandidates } from '../composables/useFacts'
import { useMatchPage } from '../composables/useMatchPage'
import CandidateStates from '../components/CandidateStates.vue'

/** Match a game with a metadata source (IGDB, Wikipedia …): pick the source and the
 * entry, then review what it would change (MetadataReviewView). */
const { t } = useI18n()
const { route, router, workId, source, work, providers, label, back, typed, query, search } =
  useMatchPage()
/** Every switched-on metadata source: the page asks one at a time. */
const sources = computed(() =>
  (providers.data.value ?? []).filter((p) => p.kind === 'metadata' && p.enabled),
)
function switchSource(name: string) {
  if (!name || name === source.value) return
  void router.replace({ params: { ...route.params, source: name }, query: route.query })
}
const candidates = useMetadataCandidates(workId, source, query)
const linked = computed(() => {
  const id = work.data.value?.external_ids[source.value]
  return id === undefined ? '' : String(id)
})

function choose(id: string) {
  void router.push({
    name: 'metadata-review',
    params: { workId: workId.value, source: source.value, externalId: id },
    query: { back: route.query.back },
  })
}
// IGDB's big cover for the candidates' thumbnails would be wasted bandwidth.
const thumb = (url: string) => url.replace('/t_cover_big_2x/', '/t_cover_small/')
</script>

<template>
  <div class="grid max-w-3xl gap-4 p-4 md:px-6">
    <RouterLink
      :to="back"
      class="inline-flex w-fit items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
    >
      <ArrowLeft class="size-3.5" /> {{ t('actions.back') }}
    </RouterLink>
    <header>
      <h1 class="text-lg font-semibold tracking-tight">
        {{ t('integrations.metadata.title') }}
      </h1>
      <p class="text-sm text-muted-foreground">
        <span v-if="work.data.value" class="font-medium text-foreground">
          {{ work.data.value.title }}
        </span>
        – {{ t('integrations.metadata.description', { source: label }) }}
      </p>
    </header>

    <div v-if="sources.length > 1" class="grid gap-1.5" data-testid="metadata-sources">
      <span class="font-mono text-[11px] tracking-wider text-muted-foreground uppercase">
        {{ t('integrations.metadata.source') }}
      </span>
      <ToggleGroup
        type="single"
        variant="outline"
        size="sm"
        class="w-fit"
        :model-value="source"
        @update:model-value="(v) => switchSource(String(v ?? ''))"
      >
        <ToggleGroupItem
          v-for="s in sources"
          :key="s.name"
          :value="s.name"
          class="px-3"
          :data-testid="`source-${s.name}`"
        >
          {{ s.label }}
        </ToggleGroupItem>
      </ToggleGroup>
    </div>
    <p
      v-if="$te(`integrations.metadata.offers.${source}`)"
      class="-mt-2 text-xs text-muted-foreground"
      data-testid="source-offers"
    >
      {{ t(`integrations.metadata.offers.${source}`) }}
    </p>

    <div
      v-if="linked"
      class="flex flex-wrap items-center gap-3 rounded-lg border bg-card px-3 py-2.5 text-sm"
      data-testid="current-link"
    >
      <span class="flex-1">
        {{ t('integrations.metadata.linked', { source: label }) }}
        <span class="tabular font-mono text-xs text-muted-foreground">#{{ linked }}</span>
      </span>
      <Button size="sm" variant="outline" data-testid="refill" @click="choose(linked)">
        <RefreshCw class="size-4" /> {{ t('integrations.metadata.refill') }}
      </Button>
    </div>

    <form class="flex gap-2" data-testid="metadata-search" @submit.prevent="search">
      <label class="relative flex flex-1 items-center">
        <Search class="pointer-events-none absolute left-2.5 size-4 text-muted-foreground" />
        <span class="sr-only">{{ t('integrations.facts.search') }}</span>
        <Input
          v-model="typed"
          class="pl-8"
          :placeholder="work.data.value?.title"
          data-testid="metadata-query"
        />
      </label>
      <Button type="submit" variant="outline">{{ t('integrations.facts.search') }}</Button>
    </form>

    <CandidateStates
      :pending="candidates.isPending.value"
      :error="candidates.isError.value ? (candidates.error.value?.message ?? '') : undefined"
      :empty="!candidates.data.value?.length"
      row-class="h-20"
    >
      <ul class="divide-y rounded-lg border bg-card" data-testid="metadata-candidates">
        <li
          v-for="c in candidates.data.value"
          :key="c.external_id"
          class="flex items-center gap-3 px-3 py-2.5"
        >
          <img
            v-if="c.cover_url"
            :src="thumb(c.cover_url)"
            alt=""
            loading="lazy"
            class="h-16 w-12 shrink-0 rounded-sm object-cover"
          />
          <div v-else class="h-16 w-12 shrink-0 rounded-sm bg-muted" />
          <div class="min-w-0 flex-1">
            <p class="font-medium">
              {{ c.title }}
              <span v-if="c.year" class="tabular font-mono text-xs text-muted-foreground">
                {{ c.year }}
              </span>
            </p>
            <p class="truncate text-xs text-muted-foreground">{{ c.platforms.join(' · ') }}</p>
            <p v-if="c.summary" class="line-clamp-1 text-xs text-muted-foreground">
              {{ c.summary }}
            </p>
          </div>
          <Button
            size="sm"
            :variant="c.external_id === linked ? 'outline' : 'default'"
            :data-testid="`choose-${c.external_id}`"
            @click="choose(c.external_id)"
          >
            {{ t('integrations.facts.choose') }}
          </Button>
        </li>
      </ul>
    </CandidateStates>
  </div>
</template>
