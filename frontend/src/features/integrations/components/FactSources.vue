<script setup lang="ts">
import { useAuthStore } from '@/stores/auth'
import { ExternalLink, Link2 } from '@lucide/vue'
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'
import type { Fact } from '@/api/types'
import { useProviders } from '@/features/library/composables/useReference'

/** Under the game's facts: where they come from (link to the source's page) and a way to
 * fix the match – one line per active facts source. */
const props = defineProps<{ workId: string; facts: Record<string, Fact> }>()
const { t } = useI18n()
const route = useRoute()
const providers = useProviders()
const sources = computed(() =>
  (providers.data.value ?? []).filter((p) => p.kind === 'facts' && p.enabled),
)
const auth = useAuthStore()
const matchLink = (source: string) => ({
  name: 'fact-match',
  params: { workId: props.workId, source },
  query: { back: route.fullPath },
})
</script>

<template>
  <ul
    v-if="sources.length"
    class="mt-3 grid gap-1 border-t pt-3 text-xs text-muted-foreground"
    data-testid="fact-sources"
  >
    <li v-for="source in sources" :key="source.name" class="flex flex-wrap items-center gap-x-2">
      <template v-if="facts[source.name]?.status === 'ok' && facts[source.name]?.url">
        <a
          :href="facts[source.name]!.url"
          target="_blank"
          rel="noopener"
          class="inline-flex items-center gap-1 hover:text-foreground"
        >
          {{ t('integrations.facts.open', { source: source.label }) }}
          <ExternalLink class="size-3" />
        </a>
      </template>
      <span v-else-if="facts[source.name]?.status === 'missing'">
        {{ t('integrations.facts.notFound', { source: source.label }) }}
      </span>
      <span v-else>{{ source.label }}</span>
      <RouterLink
        v-if="auth.isAdmin"
        :to="matchLink(source.name)"
        class="inline-flex items-center gap-1 text-primary hover:underline"
        :data-testid="`match-${source.name}`"
      >
        <Link2 class="size-3" /> {{ t('integrations.facts.match') }}
      </RouterLink>
    </li>
  </ul>
</template>
