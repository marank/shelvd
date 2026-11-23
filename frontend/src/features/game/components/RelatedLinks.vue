<script setup lang="ts">
// Where to go from here: the same page focused on the release or the game (the levels the
// page isn't on already), and the game at the sources we know an address for.
import { Disc3, ExternalLink, Gamepad2 } from '@lucide/vue'
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import type { Release } from '@/api/types'
import type { Focus } from '../composables/useGamePage'
import { useProviders } from '@/features/library/composables/useReference'

const props = defineProps<{ release: Release; focus: Focus }>()
const { t } = useI18n()
const providers = useProviders()
const external = computed(() =>
  Object.values(props.release.facts)
    .filter((fact) => fact.url)
    .map((fact) => ({
      url: fact.url,
      label: providers.data.value?.find((p) => p.name === fact.source)?.label ?? fact.source,
    })),
)
</script>

<template>
  <ul class="divide-y rounded-lg border bg-card text-sm">
    <li v-if="focus !== 'work'">
      <RouterLink
        :to="{ name: 'work', params: { workId: release.work_id } }"
        class="flex items-center gap-2 px-3 py-2.5 hover:bg-muted/50"
        data-testid="link-work"
      >
        <Gamepad2 class="size-4 text-muted-foreground" /> {{ t('game.toGame') }}
      </RouterLink>
    </li>
    <li v-if="focus === 'item'">
      <RouterLink
        :to="{ name: 'release', params: { releaseId: release.id } }"
        class="flex items-center gap-2 px-3 py-2.5 hover:bg-muted/50"
        data-testid="link-release"
      >
        <Disc3 class="size-4 text-muted-foreground" /> {{ t('game.toRelease') }}
      </RouterLink>
    </li>
    <li v-for="link in external" :key="link.url">
      <a
        :href="link.url"
        target="_blank"
        rel="noopener noreferrer"
        class="flex items-center gap-2 px-3 py-2.5 hover:bg-muted/50"
        data-testid="link-external"
      >
        <ExternalLink class="size-4 text-muted-foreground" /> {{ link.label }}
      </a>
    </li>
  </ul>
</template>
