<script setup lang="ts">
import { Copy, ExternalLink, Globe, Lock } from '@lucide/vue'
import { toast } from 'vue-sonner'
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { publicListUrl, usePublicLink } from '../composables/useLists'

/** Turn a list's public link on/off, copy and open it. */
const props = defineProps<{ listId: string; token: string | null }>()
const { t } = useI18n()
const toggle = usePublicLink(() => props.listId)
const url = computed(() => (props.token ? publicListUrl(props.token) : ''))

async function setEnabled(enabled: boolean) {
  try {
    await toggle.mutateAsync(enabled)
    toast.success(t(enabled ? 'lists.linkEnabled' : 'lists.linkDisabled'))
  } catch (error) {
    toast.error(error instanceof Error ? error.message : t('errors.generic'))
  }
}

async function copy() {
  try {
    await navigator.clipboard.writeText(url.value)
    toast.success(t('lists.linkCopied'))
  } catch {
    toast.error(t('lists.copyFailed'))
  }
}
</script>

<template>
  <section class="grid gap-3 rounded-lg border bg-card p-4" data-testid="public-link">
    <div class="flex flex-wrap items-center justify-between gap-2">
      <h2
        class="flex items-center gap-2 font-mono text-[11px] tracking-wider text-muted-foreground uppercase"
      >
        <Globe v-if="token" class="size-3.5" />
        <Lock v-else class="size-3.5" />
        {{ t('lists.publicLink') }}
      </h2>
      <Button
        v-if="token"
        type="button"
        variant="ghost"
        size="sm"
        data-testid="disable-link"
        :disabled="toggle.isPending.value"
        @click="setEnabled(false)"
      >
        {{ t('lists.disableLink') }}
      </Button>
      <Button
        v-else
        type="button"
        variant="outline"
        size="sm"
        data-testid="enable-link"
        :disabled="toggle.isPending.value"
        @click="setEnabled(true)"
      >
        {{ t('lists.enableLink') }}
      </Button>
    </div>
    <p class="text-sm text-muted-foreground">
      {{ token ? t('lists.publicLinkOn') : t('lists.publicLinkOff') }}
    </p>
    <div v-if="token" class="flex flex-col gap-2 sm:flex-row">
      <Input
        :model-value="url"
        readonly
        data-testid="link-url"
        class="font-mono text-xs"
        :aria-label="t('lists.publicLink')"
        @focus="($event.target as HTMLInputElement).select()"
      />
      <div class="flex gap-2">
        <Button
          type="button"
          variant="outline"
          size="sm"
          class="h-8"
          data-testid="copy-link"
          @click="copy"
        >
          <Copy />
          {{ t('actions.copy') }}
        </Button>
        <Button variant="outline" size="sm" class="h-8" as-child>
          <a :href="url" target="_blank" rel="noopener">
            <ExternalLink />
            {{ t('lists.openLink') }}
          </a>
        </Button>
      </div>
    </div>
  </section>
</template>
