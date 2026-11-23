<script setup lang="ts">
import { collect } from '@/addons'
import {
  CircleAlert,
  Clock,
  Database,
  ExternalLink,
  Gamepad2,
  Image,
  Settings2,
  Timer,
  type LucideIcon,
} from '@lucide/vue'
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import type { Integration, Provider } from '@/api/types'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { useProviders } from '@/features/library/composables/useReference'
import { useAuthStore } from '@/stores/auth'
import { useIntegrations } from '../composables/useIntegrations'

/** Every external service: what it's for, whether it's on, who to credit. Admins also
 * see the last success/error and a link to set each one up. */
const { t, d } = useI18n()
const auth = useAuthStore()
const staff = computed(() => !!auth.user?.is_staff)
const providers = useProviders()
const integrations = useIntegrations(staff)

const KINDS = ['metadata', 'facts', 'covers', 'playtime'] as const
const ICONS: Record<string, LucideIcon> = {
  metadata: Gamepad2,
  facts: Clock,
  covers: Image,
  playtime: Timer,
}
/** Whom to credit, and where. */
const SITES: Record<string, string> = {
  igdb: 'https://www.igdb.com',
  wikipedia: 'https://www.wikipedia.org',
  hltb: 'https://howlongtobeat.com',
  opencritic: 'https://opencritic.com',
  thegamesdb: 'https://thegamesdb.net',
  screenscraper: 'https://www.screenscraper.fr',
  // Add-ons' integrations (play time services …) bring their own links.
  ...Object.assign({}, ...collect('integrationLinks')),
}
const details = computed(
  () => new Map((integrations.data.value ?? []).map((i) => [i.key, i] as const)),
)
const groups = computed(() =>
  KINDS.map((kind) => ({
    kind,
    entries: (providers.data.value ?? []).filter((p) => p.kind === kind),
  })).filter((g) => g.entries.length),
)
const credited = computed(() => (providers.data.value ?? []).filter((p) => p.enabled))

function status(provider: Provider, detail?: Integration) {
  if (provider.enabled) return 'active'
  return detail?.enabled ? 'incomplete' : 'off'
}
const when = (value: string) => d(new Date(value), 'short')
/** An error counts until a later success. */
const currentError = (i: Integration) =>
  !!i.last_error &&
  !!i.last_error_at &&
  (!i.last_ok_at || new Date(i.last_error_at) > new Date(i.last_ok_at))
const label = 'font-mono text-[11px] uppercase tracking-wider text-muted-foreground'
</script>

<template>
  <header class="border-b px-4 py-3 md:px-6">
    <h1 class="text-lg font-semibold tracking-tight">{{ t('integrations.title') }}</h1>
    <p class="text-sm text-muted-foreground">{{ t('integrations.subtitle') }}</p>
  </header>

  <div class="grid max-w-3xl gap-6 p-4 md:px-6">
    <p v-if="!staff" class="text-sm text-muted-foreground">{{ t('integrations.adminOnly') }}</p>
    <div v-if="providers.isPending.value" class="grid gap-2">
      <Skeleton v-for="n in 3" :key="n" class="h-24 rounded-lg" />
    </div>

    <section v-for="group in groups" :key="group.kind" class="grid gap-2">
      <h2 :class="label" class="flex items-center gap-1.5">
        <component :is="ICONS[group.kind]" class="size-3.5" />
        {{ t(`integrations.kinds.${group.kind}`) }}
      </h2>
      <article
        v-for="provider in group.entries"
        :key="provider.name"
        class="grid gap-2 rounded-lg border bg-card p-4"
        :data-testid="`integration-${provider.name}`"
      >
        <div class="flex flex-wrap items-center gap-2">
          <h3 class="font-medium">{{ provider.label }}</h3>
          <Badge
            :variant="provider.enabled ? 'secondary' : 'outline'"
            class="font-mono text-[11px]"
            data-testid="status"
          >
            <span
              class="size-1.5 rounded-full"
              :class="
                provider.enabled
                  ? 'bg-success'
                  : status(provider, details.get(provider.name)) === 'incomplete'
                    ? 'bg-warning'
                    : 'bg-muted-foreground/50'
              "
            />
            {{ t(`integrations.status.${status(provider, details.get(provider.name))}`) }}
          </Badge>
          <Badge
            v-if="details.get(provider.name)?.unofficial"
            variant="outline"
            class="border-warning/40 text-warning"
            :title="t('integrations.unofficialText')"
          >
            {{ t('integrations.unofficial') }}
          </Badge>
          <Button
            v-if="staff"
            as-child
            variant="outline"
            size="sm"
            class="ml-auto"
            :data-testid="`set-up-${provider.name}`"
          >
            <RouterLink :to="{ name: 'integration-edit', params: { key: provider.name } }">
              <Settings2 class="size-4" /> {{ t('integrations.setUp') }}
            </RouterLink>
          </Button>
        </div>
        <p class="text-sm text-muted-foreground">{{ t(`integrations.about.${provider.name}`) }}</p>
        <template v-if="details.get(provider.name)">
          <p
            v-if="currentError(details.get(provider.name)!)"
            class="flex items-start gap-1.5 text-xs text-destructive"
            data-testid="last-error"
          >
            <CircleAlert class="mt-px size-3.5 shrink-0" />
            {{
              t('integrations.lastError', {
                time: when(details.get(provider.name)!.last_error_at!),
                message: details.get(provider.name)!.last_error,
              })
            }}
          </p>
          <p v-if="details.get(provider.name)!.last_ok_at" class="text-xs text-muted-foreground">
            {{ t('integrations.lastOk', { time: when(details.get(provider.name)!.last_ok_at!) }) }}
          </p>
        </template>
      </article>
    </section>

    <section class="grid gap-2 rounded-lg border bg-card p-4">
      <h2 class="flex items-center gap-2 font-medium">
        <Database class="size-4 text-muted-foreground" />
        {{ t('integrations.local.title') }}
      </h2>
      <p class="text-sm text-muted-foreground">{{ t('integrations.local.text') }}</p>
    </section>

    <section v-if="credited.length" class="grid gap-1 border-t pt-4" data-testid="attribution">
      <a
        v-for="provider in credited"
        :key="provider.name"
        :href="SITES[provider.name]"
        target="_blank"
        rel="noopener"
        class="inline-flex w-fit items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
      >
        {{ t(`integrations.attribution.${provider.name}`) }}
        <ExternalLink class="size-3" />
      </a>
    </section>
  </div>
</template>
