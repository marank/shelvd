<script setup lang="ts">
import { Search } from '@lucide/vue'
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { toast } from 'vue-sonner'
import BackButton from '@/components/app/BackButton.vue'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Skeleton } from '@/components/ui/skeleton'
import { KIND_ICONS, describeRoute, describedPage, type DescribedKind } from '@/lib/terms'
import ImageTile from '../components/ImageTile.vue'
import {
  useCommonsImages,
  useDescribers,
  useImageCandidates,
  useSubject,
  useTakeImage,
  type ImageTarget,
} from '../composables/useTermPages'
import { useTermRoute } from '../composables/useTermRoute'

/** A company's, series' or platform's picture from the entries it's linked to (every logo
 * a Wikidata entry lists – older ones too –, photos, IGDB's …) or found on Wikimedia
 * Commons. A term takes one with a click; a platform as its logo, its photo of the device
 * or its badge's icon (a small logo). */
const { t } = useI18n()
const router = useRouter()
const { kind, termId } = useTermRoute()
// Only companies, series and platforms have this page (see the routes).
const describedKind = computed(() => kind.value as DescribedKind)
const subject = useSubject(describedKind, termId)
const forPlatform = computed(() => describedKind.value === 'platforms')
const targets = computed<ImageTarget[] | null>(() =>
  forPlatform.value ? ['image', 'photo', 'icon'] : null,
)
const describers = useDescribers(kind)
const candidates = useImageCandidates(describedKind, termId)
const typed = ref('')
const query = ref('')
const commons = useCommonsImages(query)
const canSearch = computed(() => describers.value.some((d) => d.name === 'wikipedia'))
const takeImage = useTakeImage(describedKind)
const taking = ref('')
const broken = ref(new Set<string>())
const detail = computed(() => describedPage(describedKind.value, termId.value))
const sourceLabel = (name: string) => describers.value.find((d) => d.name === name)?.label ?? name
/** What the page has now: picture (logo), photo, badge icon. */
const current = computed(() =>
  (
    [
      ['image', subject.value?.image_url],
      ['photo', subject.value?.photo_url],
      ['icon', subject.value?.icon_url],
    ] as const
  ).filter(([slot, url]) => slot === 'image' || url),
)

function search() {
  query.value = typed.value.trim()
}

async function take(token: string, target: ImageTarget) {
  taking.value = token
  try {
    await takeImage.mutateAsync({ termId: termId.value, token, target })
    toast.success(t(`terms.images.saved.${target}`))
    void router.push(detail.value)
  } catch (error) {
    toast.error((error as Error).message)
  } finally {
    taking.value = ''
  }
}
</script>

<template>
  <div class="flex-1 overflow-y-auto">
    <div class="mx-auto grid max-w-3xl gap-4 px-4 py-4 md:px-6 md:py-6">
      <BackButton :fallback="detail" />
      <header class="flex items-start gap-3">
        <div
          v-for="[slot, url] in current"
          :key="slot"
          class="grid grid-cols-1 grid-rows-1 size-16 shrink-0 place-items-center rounded-xl border bg-card p-2"
          :title="forPlatform ? t(`terms.images.slots.${slot}`) : undefined"
          :data-testid="`term-${slot}-current`"
        >
          <img v-if="url" :src="url" alt="" class="max-h-full max-w-full object-contain" />
          <component :is="KIND_ICONS[kind]" v-else class="size-6 text-muted-foreground/60" />
        </div>
        <div>
          <p class="font-mono text-[11px] tracking-wider text-muted-foreground uppercase">
            {{ subject?.name }}
          </p>
          <h1 class="text-lg font-semibold tracking-tight">{{ t('terms.images.title') }}</h1>
          <p class="text-sm text-muted-foreground">
            {{ t(forPlatform ? 'terms.images.platformHint' : 'terms.images.hint') }}
          </p>
        </div>
      </header>

      <div v-if="candidates.isPending.value" class="grid grid-cols-2 gap-3 sm:grid-cols-3">
        <Skeleton v-for="i in 3" :key="i" class="aspect-[4/3] rounded-lg" />
      </div>
      <p v-else-if="candidates.isError.value" class="text-sm text-destructive" role="alert">
        {{ candidates.error.value?.message }}
      </p>
      <div
        v-else-if="!candidates.data.value?.length"
        class="grid gap-2 rounded-lg border border-dashed px-4 py-6 text-sm text-muted-foreground"
        data-testid="term-images-none"
      >
        <p>{{ t('terms.images.none') }}</p>
        <p class="flex flex-wrap gap-x-3">
          <RouterLink
            v-for="d in describers"
            :key="d.name"
            :to="describeRoute(describedKind, termId, d.name)"
            class="text-primary hover:underline"
          >
            {{ t('terms.describe.menu', { source: d.label }) }}
          </RouterLink>
        </p>
      </div>
      <ul v-else class="grid grid-cols-2 gap-3 sm:grid-cols-3" data-testid="term-images">
        <li v-for="c in candidates.data.value" :key="c.token">
          <ImageTile
            :candidate="c"
            :source-label="sourceLabel(c.source)"
            :targets="targets"
            :taking="taking === c.token"
            :disabled="!!taking"
            :broken="broken.has(c.token)"
            @take="take(c.token, $event)"
            @broken="broken.add(c.token)"
          />
        </li>
      </ul>

      <section v-if="canSearch" class="grid gap-3 border-t pt-4" data-testid="commons-search">
        <div>
          <h2 class="text-sm font-semibold">{{ t('terms.images.commons') }}</h2>
          <p class="text-sm text-muted-foreground">{{ t('terms.images.commonsHint') }}</p>
        </div>
        <form class="flex gap-2" @submit.prevent="search">
          <label class="relative flex flex-1 items-center">
            <Search class="pointer-events-none absolute left-2.5 size-4 text-muted-foreground" />
            <span class="sr-only">{{ t('terms.search') }}</span>
            <Input
              v-model="typed"
              class="pl-8"
              :placeholder="t('terms.images.commonsPlaceholder', { name: subject?.name ?? '' })"
              data-testid="commons-query"
            />
          </label>
          <Button type="submit" variant="outline">{{ t('terms.search') }}</Button>
        </form>
        <div v-if="query && commons.isPending.value" class="grid grid-cols-2 gap-3 sm:grid-cols-3">
          <Skeleton v-for="i in 3" :key="i" class="aspect-[4/3] rounded-lg" />
        </div>
        <p v-else-if="commons.isError.value" class="text-sm text-destructive" role="alert">
          {{ commons.error.value?.message }}
        </p>
        <p
          v-else-if="query && !commons.data.value?.length"
          class="text-sm text-muted-foreground"
          data-testid="commons-none"
        >
          {{ t('terms.none') }}
        </p>
        <ul
          v-else-if="commons.data.value?.length"
          class="grid grid-cols-2 gap-3 sm:grid-cols-3"
          data-testid="commons-images"
        >
          <li v-for="c in commons.data.value" :key="c.token">
            <ImageTile
              :candidate="c"
              source-label="Wikimedia Commons"
              :targets="targets"
              :taking="taking === c.token"
              :disabled="!!taking"
              :broken="broken.has(c.token)"
              @take="take(c.token, $event)"
              @broken="broken.add(c.token)"
            />
          </li>
        </ul>
      </section>
    </div>
  </div>
</template>
