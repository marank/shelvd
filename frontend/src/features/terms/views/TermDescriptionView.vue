<script setup lang="ts">
import { BookOpen, Check, Image, Search } from '@lucide/vue'
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import { toast } from 'vue-sonner'
import BackButton from '@/components/app/BackButton.vue'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { Input } from '@/components/ui/input'
import { Skeleton } from '@/components/ui/skeleton'
import { Spinner } from '@/components/ui/spinner'
import { languageName } from '@/lib/displayNames'
import { KIND_ICONS, describeRoute, describedPage, type DescribedKind } from '@/lib/terms'
import {
  useApplyDescription,
  useDescribers,
  useDescriptionCandidates,
  useSubject,
} from '../composables/useTermPages'
import { useTermRoute } from '../composables/useTermRoute'

/** A company's, series' or platform's description from a source (Wikipedia, IGDB): pick the entry
 * that is it, its text becomes the description and – if wanted – its logo the picture.
 * The other sources for the kind are a click away. */
const { t, locale } = useI18n()
const route = useRoute()
const router = useRouter()
const { kind, termId } = useTermRoute()
// Only companies, series and platforms have this page (see the routes).
const describedKind = computed(() => kind.value as DescribedKind)
const source = computed(() => String(route.params.source))
const subject = useSubject(describedKind, termId)
const describers = useDescribers(kind)
const label = computed(
  () => describers.value.find((p) => p.name === source.value)?.label ?? source.value,
)
const others = computed(() => describers.value.filter((p) => p.name !== source.value))
const typed = ref('')
const query = ref('')
const candidates = useDescriptionCandidates(describedKind, termId, source, query)
const applyDescription = useApplyDescription(describedKind)
const taking = ref('')
// Logos replace the picture: on by default only while there is none.
const withLogo = ref(true)
watch(
  () => subject.value?.image_url,
  (image) => (withLogo.value = !image),
  { immediate: true },
)
const anyLogo = computed(() => candidates.data.value?.some((c) => c.has_image) ?? false)
const detail = computed(() => describedPage(describedKind.value, termId.value))

function search() {
  query.value = typed.value.trim()
}

async function take(externalId: string, hasImage: boolean) {
  taking.value = externalId
  try {
    const applied = await applyDescription.mutateAsync({
      termId: termId.value,
      source: source.value,
      externalId,
      image: withLogo.value && hasImage,
    })
    if (withLogo.value && hasImage && !applied.image) toast.warning(t('terms.describe.logoFailed'))
    toast.success(t(applied.image ? 'terms.describe.takenWithLogo' : 'terms.describe.taken'))
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
      <header>
        <p
          class="inline-flex items-center gap-1.5 font-mono text-[11px] tracking-wider text-muted-foreground uppercase"
        >
          <component :is="KIND_ICONS[kind]" class="size-3.5" />
          {{ subject?.name }}
        </p>
        <h1 class="text-lg font-semibold tracking-tight">
          {{ t('terms.describe.title', { source: label }) }}
        </h1>
        <p class="text-sm text-muted-foreground">
          {{ t('terms.describe.hint', { source: label }) }}
        </p>
        <p v-if="others.length" class="mt-1 flex flex-wrap gap-x-3 text-sm">
          <RouterLink
            v-for="o in others"
            :key="o.name"
            :to="describeRoute(describedKind, termId, o.name)"
            replace
            class="text-primary hover:underline"
            :data-testid="`description-source-${o.name}`"
          >
            {{ t('terms.describe.askOther', { source: o.label }) }}
          </RouterLink>
        </p>
      </header>

      <form class="flex gap-2" data-testid="description-search" @submit.prevent="search">
        <label class="relative flex flex-1 items-center">
          <Search class="pointer-events-none absolute left-2.5 size-4 text-muted-foreground" />
          <span class="sr-only">{{ t('terms.search') }}</span>
          <Input
            v-model="typed"
            class="pl-8"
            :placeholder="subject?.name"
            data-testid="description-query"
          />
        </label>
        <Button type="submit" variant="outline">{{ t('terms.search') }}</Button>
      </form>

      <label
        v-if="anyLogo"
        class="flex cursor-pointer items-start gap-3 rounded-lg border bg-card px-3 py-3"
      >
        <Checkbox
          :model-value="withLogo"
          @update:model-value="withLogo = $event === true"
          class="mt-0.5"
          data-testid="description-logo"
        />
        <span class="grid gap-0.5">
          <span class="text-sm font-medium">{{ t('terms.describe.logo') }}</span>
          <span class="text-xs text-muted-foreground">
            {{
              subject?.image_url ? t('terms.describe.logoReplaces') : t('terms.describe.logoHint')
            }}
          </span>
        </span>
      </label>

      <div v-if="candidates.isPending.value" class="grid gap-1">
        <Skeleton v-for="i in 3" :key="i" class="h-24 rounded-md" />
      </div>
      <p v-else-if="candidates.isError.value" class="text-sm text-destructive" role="alert">
        {{ candidates.error.value?.message }}
      </p>
      <p v-else-if="!candidates.data.value?.length" class="text-sm text-muted-foreground">
        {{ t('terms.none') }}
      </p>
      <ul v-else class="divide-y rounded-lg border bg-card" data-testid="description-candidates">
        <li
          v-for="c in candidates.data.value"
          :key="c.external_id"
          class="flex flex-col gap-2 px-3 py-3 sm:flex-row sm:items-start"
        >
          <BookOpen class="mt-0.5 hidden size-4 shrink-0 text-muted-foreground sm:block" />
          <div class="min-w-0 flex-1">
            <p class="flex flex-wrap items-center gap-2 font-medium">
              {{ c.title }}
              <Badge
                v-if="c.confident"
                variant="secondary"
                class="gap-1 font-normal"
                :data-testid="`confident-${c.external_id}`"
              >
                <Check class="size-3" />
                {{ t('terms.describe.confident') }}
              </Badge>
              <Badge
                v-if="c.language && c.language !== locale"
                variant="outline"
                class="font-normal"
              >
                {{ languageName(c.language, locale) }}
              </Badge>
              <Badge v-if="c.has_image" variant="outline" class="gap-1 font-normal">
                <Image class="size-3" />
                {{ t('terms.describe.hasLogo') }}
              </Badge>
            </p>
            <p v-if="c.label" class="text-xs text-muted-foreground">{{ c.label }}</p>
            <p v-if="c.text" class="mt-1 line-clamp-3 text-sm text-muted-foreground">
              {{ c.text }}
            </p>
            <p v-else class="mt-1 text-sm text-muted-foreground italic">
              {{ t('terms.describe.factsOnly') }}
            </p>
          </div>
          <Button
            size="sm"
            class="self-end sm:self-start"
            :disabled="!!taking"
            :data-testid="`take-${c.external_id}`"
            @click="take(c.external_id, c.has_image)"
          >
            <Spinner v-if="taking === c.external_id" />
            {{
              !c.text
                ? t('terms.describe.takeFacts')
                : subject?.description
                  ? t('terms.describe.replace')
                  : t('terms.describe.take')
            }}
          </Button>
        </li>
      </ul>
    </div>
  </div>
</template>
