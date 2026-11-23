<script setup lang="ts">
import { Copy, ExternalLink } from '@lucide/vue'
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { toast } from 'vue-sonner'
import type { Library } from '@/api/types'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Spinner } from '@/components/ui/spinner'
import { errorMessage } from '../../composables/format'
import { useLibraryMutations } from '../../composables/useLibrarySettings'

const props = defineProps<{ library: Library }>()
const { t } = useI18n()
const { enableLink, disableLink } = useLibraryMutations(() => props.library.id)
const busy = computed(() => enableLink.isPending.value || disableLink.isPending.value)
const url = computed(() =>
  props.library.public_token ? `${window.location.origin}/share/${props.library.public_token}` : '',
)

async function toggle() {
  try {
    if (props.library.public_token) {
      await disableLink.mutateAsync()
      toast.success(t('manage.settings.linkOff'))
    } else {
      await enableLink.mutateAsync()
      toast.success(t('manage.settings.linkOn'))
    }
  } catch (e) {
    toast.error(errorMessage(e, t('errors.generic')))
  }
}

async function copy() {
  try {
    await navigator.clipboard.writeText(url.value)
    toast.success(t('actions.copied'))
  } catch {
    toast.error(t('manage.settings.copyFailed'))
  }
}
</script>

<template>
  <Card data-testid="settings-public">
    <CardHeader>
      <CardTitle>{{ t('manage.settings.publicLink') }}</CardTitle>
      <CardDescription>{{ t('manage.settings.publicHint') }}</CardDescription>
    </CardHeader>
    <CardContent class="grid gap-3">
      <div class="flex flex-wrap items-center gap-3">
        <Button
          :variant="library.public_token ? 'outline' : 'default'"
          data-testid="public-toggle"
          :disabled="busy"
          @click="toggle"
        >
          <Spinner v-if="busy" />
          {{
            library.public_token
              ? t('manage.settings.disableLink')
              : t('manage.settings.enableLink')
          }}
        </Button>
        <span class="font-mono text-[11px] tracking-wider text-muted-foreground uppercase">
          {{
            library.public_token
              ? t('manage.settings.linkActive')
              : t('manage.settings.linkInactive')
          }}
        </span>
      </div>
      <div v-if="url" class="flex flex-wrap items-center gap-2">
        <Input
          :model-value="url"
          readonly
          class="min-w-0 flex-1 basis-60 font-mono text-xs"
          :aria-label="t('manage.settings.publicLink')"
          data-testid="public-url"
          @focus="($event.target as HTMLInputElement).select()"
        />
        <Button variant="outline" data-testid="public-copy" @click="copy">
          <Copy />
          {{ t('actions.copy') }}
        </Button>
        <Button as-child variant="ghost">
          <a :href="url" target="_blank" rel="noopener" data-testid="public-open">
            <ExternalLink />
            {{ t('manage.settings.open') }}
          </a>
        </Button>
      </div>
    </CardContent>
  </Card>
</template>
