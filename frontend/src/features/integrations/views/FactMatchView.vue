<script setup lang="ts">
import { ArrowLeft, ExternalLink, RefreshCw, Search } from '@lucide/vue'
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { toast } from 'vue-sonner'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { useFactCandidates, usePinFact, useUnpinFact } from '../composables/useFacts'
import { useMatchPage } from '../composables/useMatchPage'
import CandidateStates from '../components/CandidateStates.vue'

/** Choose which entry of a facts source (HowLongToBeat, OpenCritic) belongs to a game. */
const { t, n } = useI18n()
const { router, workId, source, work, label, back, typed, query, search } = useMatchPage()
const candidates = useFactCandidates(workId, source, query)
const pin = usePinFact()
const unpin = useUnpinFact()
const current = computed(() => work.data.value?.releases[0]?.facts[source.value])

async function choose(id: string) {
  try {
    await pin.mutateAsync({ workId: workId.value, source: source.value, id })
    toast.success(t('integrations.facts.chosen'))
    await router.push(back.value)
  } catch (e) {
    toast.error((e as Error).message)
  }
}
async function auto() {
  try {
    await unpin.mutateAsync({ workId: workId.value, source: source.value })
    toast.success(t('integrations.facts.autoDone'))
    await router.push(back.value)
  } catch (e) {
    toast.error((e as Error).message)
  }
}
const values = (v: Record<string, number>) =>
  Object.entries(v)
    .map(([k, value]) =>
      ['main', 'extra', 'complete'].includes(k)
        ? `${t(`itemFields.game.time_${k}`)}: ${n(value, { maximumFractionDigits: 1 })} h`
        : `${t(k === 'score' ? 'itemFields.game.critic_score' : 'itemFields.game.critic_recommended')}: ${n(Math.round(value))}`,
    )
    .join(' · ')
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
        {{ t('integrations.facts.title', { source: label }) }}
      </h1>
      <p class="text-sm text-muted-foreground">
        <span v-if="work.data.value" class="font-medium text-foreground">
          {{ work.data.value.title }}
        </span>
        – {{ t('integrations.facts.description', { source: label }) }}
      </p>
    </header>

    <p v-if="current?.status === 'ok'" class="text-sm" data-testid="current-match">
      <span class="text-muted-foreground">{{ t('integrations.facts.current') }}:</span>
      {{ current.title }}
      <span v-if="Object.keys(current.values).length" class="text-muted-foreground">
        ({{ values(current.values) }})
      </span>
    </p>

    <form class="flex gap-2" data-testid="fact-search" @submit.prevent="search">
      <label class="relative flex flex-1 items-center">
        <Search class="pointer-events-none absolute left-2.5 size-4 text-muted-foreground" />
        <span class="sr-only">{{ t('integrations.facts.search') }}</span>
        <Input
          v-model="typed"
          class="pl-8"
          :placeholder="work.data.value?.title"
          data-testid="fact-query"
        />
      </label>
      <Button type="submit" variant="outline">{{ t('integrations.facts.search') }}</Button>
      <Button type="button" variant="ghost" data-testid="auto-match" @click="auto">
        <RefreshCw class="size-4" /> {{ t('integrations.facts.auto') }}
      </Button>
    </form>

    <CandidateStates
      :pending="candidates.isPending.value"
      :error="candidates.isError.value ? (candidates.error.value?.message ?? '') : undefined"
      :empty="!candidates.data.value?.length"
      row-class="h-14"
    >
      <ul class="divide-y rounded-lg border bg-card" data-testid="fact-candidates">
        <li
          v-for="c in candidates.data.value"
          :key="c.external_id"
          class="flex flex-wrap items-center gap-3 px-3 py-2.5"
        >
          <div class="min-w-0 flex-1">
            <p class="font-medium">
              {{ c.title }}
              <span v-if="c.year" class="tabular font-mono text-xs text-muted-foreground">
                {{ c.year }}
              </span>
            </p>
            <p class="truncate text-xs text-muted-foreground">
              {{ [c.platforms, values(c.values)].filter(Boolean).join(' · ') }}
            </p>
          </div>
          <a
            :href="c.url"
            target="_blank"
            rel="noopener"
            class="text-muted-foreground hover:text-foreground"
            :aria-label="t('integrations.facts.open', { source: label })"
          >
            <ExternalLink class="size-4" />
          </a>
          <Button size="sm" :data-testid="`choose-${c.external_id}`" @click="choose(c.external_id)">
            {{ t('integrations.facts.choose') }}
          </Button>
        </li>
      </ul>
    </CandidateStates>
  </div>
</template>
