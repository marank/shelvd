<script setup lang="ts">
import { ArrowLeft, Search } from '@lucide/vue'
import { computed, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import { toast } from 'vue-sonner'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Skeleton } from '@/components/ui/skeleton'
import { useItemById, useItemMutations, useRelease } from '@/features/items/composables/useItem'
import { useProviders } from '@/features/library/composables/useReference'
import { backTarget } from '@/features/works/composables/form'
import { coverPreview, useApplyCover, useCoverCandidates } from '../composables/useFacts'

/** Covers from the covers sources for one release; clicking one stores it locally – as the
 * release's cover (catalog), or with `?item=…` only as that copy's own cover. */
const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const releaseId = computed(() => String(route.params.releaseId))
const release = useRelease(releaseId)
const providers = useProviders()
const sourceLabel = (name: string) =>
  providers.data.value?.find((p) => p.name === name)?.label ?? name
const hasSources = computed(() =>
  (providers.data.value ?? []).some((p) => p.kind === 'covers' && p.enabled),
)
const typed = ref('')
const query = ref('')
const candidates = useCoverCandidates(releaseId, query)

function search() {
  query.value = typed.value.trim()
}
/** Pixel size per candidate: measured from the loaded preview (the original image), until
 * then what the source says (only some sources tell). */
const measured = reactive<Record<string, string>>({})
function measure(token: string, event: Event) {
  const img = event.target as HTMLImageElement
  if (img.naturalWidth) measured[token] = `${img.naturalWidth}×${img.naturalHeight}`
}
function sizeOf(c: { token: string; width: number | null; height: number | null }) {
  return measured[c.token] ?? (c.width && c.height ? `${c.width}×${c.height}` : '')
}

const apply = useApplyCover()
const back = computed(() => backTarget(route.query.back))
const itemId = computed(() => (typeof route.query.item === 'string' ? route.query.item : ''))
// For a copy: its library comes with it.
const { libraryId } = useItemById(itemId)
const { coverFrom } = useItemMutations(libraryId)
const pending = computed(() => apply.isPending.value || coverFrom.isPending.value)

async function take(token: string) {
  try {
    if (itemId.value) {
      await coverFrom.mutateAsync({ id: itemId.value, token })
    } else {
      await apply.mutateAsync({ releaseId: releaseId.value, token })
    }
    toast.success(t('integrations.covers.taken'))
    await router.push(back.value)
  } catch (e) {
    toast.error((e as Error).message)
  }
}
</script>

<template>
  <div class="grid gap-4 p-4 md:px-6">
    <RouterLink
      :to="back"
      class="inline-flex w-fit items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
    >
      <ArrowLeft class="size-3.5" /> {{ t('actions.back') }}
    </RouterLink>
    <header>
      <h1 class="text-lg font-semibold tracking-tight">{{ t('integrations.covers.title') }}</h1>
      <p class="text-sm text-muted-foreground">
        <span v-if="release.data.value" class="font-medium text-foreground">
          {{ release.data.value.title }} · {{ release.data.value.platform.name }}
        </span>
        –
        {{ t(itemId ? 'integrations.covers.descriptionCopy' : 'integrations.covers.description') }}
      </p>
    </header>

    <form v-if="hasSources" class="flex gap-2" data-testid="cover-search" @submit.prevent="search">
      <label class="relative flex flex-1 items-center">
        <Search class="pointer-events-none absolute left-2.5 size-4 text-muted-foreground" />
        <span class="sr-only">{{ t('integrations.facts.search') }}</span>
        <Input
          v-model="typed"
          class="pl-8"
          :placeholder="release.data.value?.title"
          data-testid="cover-query"
        />
      </label>
      <Button type="submit" variant="outline">{{ t('integrations.facts.search') }}</Button>
    </form>

    <p
      v-if="providers.data.value && !hasSources"
      class="text-sm text-muted-foreground"
      data-testid="no-cover-sources"
    >
      {{ t('integrations.covers.noSources') }}
    </p>
    <div v-else-if="candidates.isPending.value" class="flex flex-wrap gap-3">
      <Skeleton v-for="i in 6" :key="i" class="h-52 w-36 rounded-md" />
    </div>
    <p v-else-if="!candidates.data.value?.length" class="text-sm text-muted-foreground">
      {{ t('integrations.covers.none') }}
    </p>
    <ul v-else class="flex flex-wrap items-start gap-3" data-testid="cover-candidates">
      <li v-for="c in candidates.data.value" :key="c.token">
        <button
          type="button"
          class="group grid w-36 gap-1 rounded-md p-1 text-left hover:bg-accent focus-visible:ring-2 focus-visible:ring-ring/50 focus-visible:outline-none"
          :title="t('integrations.covers.take')"
          :disabled="pending"
          data-testid="cover-candidate"
          @click="take(c.token)"
        >
          <span class="relative block">
            <img
              :src="coverPreview(c.token)"
              :alt="c.title"
              loading="lazy"
              class="w-full rounded-sm border bg-muted object-contain"
              @load="measure(c.token, $event)"
            />
            <span
              v-if="sizeOf(c)"
              class="tabular absolute right-1 bottom-1 rounded-sm bg-background/85 px-1 py-0.5 font-mono text-[10px] text-foreground shadow-xs"
              data-testid="cover-size"
            >
              {{ sizeOf(c) }}
            </span>
          </span>
          <span class="truncate text-xs font-medium">{{ c.title }}</span>
          <span class="truncate font-mono text-[10px] text-muted-foreground uppercase">
            {{ [sourceLabel(c.source), c.platform, c.region].filter(Boolean).join(' · ') }}
          </span>
        </button>
      </li>
    </ul>
  </div>
</template>
