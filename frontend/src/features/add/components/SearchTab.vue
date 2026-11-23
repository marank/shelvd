<script setup lang="ts">
import { useAuthStore } from '@/stores/auth'
import { refDebounced } from '@vueuse/core'
import { Camera, CameraOff, Info, PenLine, ScanBarcode, Search, X } from '@lucide/vue'
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import type { Candidate, Release } from '@/api/types'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Spinner } from '@/components/ui/spinner'
import { usePlatforms, useProviders } from '@/features/library/composables/useReference'
import { looksLikeCode, useCatalogSearch, useProviderSearch } from '../composables/useAddApi'
import CandidateRow from './CandidateRow.vue'
import NativeSelect from '@/components/app/NativeSelect.vue'
import ReleaseRow from './ReleaseRow.vue'

const props = defineProps<{
  initialQuery?: string
  barcode?: string | null
  /** Releases the scanned barcode is already confirmed for. */
  known?: Release[]
  /** Offers the camera and takes codes typed into the field. */
  scannable?: boolean
  scanning?: boolean
  /** A game is picked: only the bar stays. */
  collapsed?: boolean
}>()
const emit = defineEmits<{
  release: [release: Release]
  candidate: [candidate: Candidate]
  manual: [title: string]
  code: [code: string]
  typing: []
  toggleScan: []
  clearBarcode: []
}>()
const { t } = useI18n()
const auth = useAuthStore()

const query = ref(props.initialQuery ?? '')
const platform = ref('')
const field = ref<{ $el: HTMLInputElement } | null>(null)
const debounced = refDebounced(query, 300)
const isCode = computed(() => !!props.scannable && looksLikeCode(query.value))
// A code isn't a title: not worth asking the catalog and IGDB about.
const params = computed(() => ({
  q: isCode.value ? '' : debounced.value,
  platform: platform.value,
}))
const ready = computed(() => !isCode.value && debounced.value.trim().length >= 2)

const platforms = usePlatforms()
const providers = useProviders()
const igdbEnabled = computed(
  () => !!providers.data.value?.some((p) => p.name === 'igdb' && p.enabled),
)
const catalog = useCatalogSearch(params)
const online = useProviderSearch(params, igdbEnabled)

function onInput(value: string | number) {
  query.value = String(value)
  emit('typing')
}

function submit() {
  if (isCode.value) emit('code', query.value)
}

onMounted(() => {
  // Ready for USB/Bluetooth scanners; no keyboard popping up over a phone's camera.
  const coarse = window.matchMedia('(pointer: coarse)').matches
  if (!(props.scanning && coarse)) field.value?.$el.focus()
})
</script>

<template>
  <div class="grid grid-cols-1 gap-4">
    <div class="sticky top-0 z-10 -mx-4 grid gap-2 border-b bg-popover px-4 py-3">
      <form
        class="grid gap-2 sm:grid-cols-[1fr_12rem_auto]"
        role="search"
        data-testid="search-form"
        @submit.prevent="submit"
      >
        <label class="relative block">
          <span class="sr-only">{{ t('add.search.label') }}</span>
          <Search
            class="pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-muted-foreground"
          />
          <Input
            ref="field"
            :model-value="query"
            type="search"
            class="pl-8"
            autocomplete="off"
            enterkeyhint="search"
            data-testid="search-input"
            :placeholder="t(scannable ? 'add.search.placeholderCode' : 'add.search.placeholder')"
            @update:model-value="onInput"
          />
        </label>
        <label class="block">
          <span class="sr-only">{{ t('fields.platform') }}</span>
          <NativeSelect v-model="platform" data-testid="search-platform">
            <option value="">{{ t('add.search.allPlatforms') }}</option>
            <option v-for="p in platforms.data.value ?? []" :key="p.id" :value="p.id">
              {{ p.name }}
            </option>
          </NativeSelect>
        </label>
        <Button
          v-if="scannable"
          type="button"
          variant="outline"
          data-testid="scan-toggle"
          :aria-pressed="scanning"
          @click="emit('toggleScan')"
        >
          <CameraOff v-if="scanning" class="size-4" />
          <Camera v-else class="size-4" />
          {{ scanning ? t('add.scan.cameraOff') : t('add.search.scan') }}
        </Button>
      </form>

      <p
        v-if="barcode"
        class="flex items-center gap-2 text-xs text-muted-foreground"
        data-testid="search-barcode"
      >
        <ScanBarcode class="size-3.5 shrink-0" />
        <span class="min-w-0 flex-1">{{ t('add.search.barcode', { code: barcode }) }}</span>
        <Button
          v-if="scannable"
          type="button"
          variant="ghost"
          size="icon-xs"
          :aria-label="t('add.search.clearBarcode')"
          data-testid="clear-barcode"
          @click="emit('clearBarcode')"
        >
          <X class="size-3.5" />
        </Button>
      </p>
    </div>

    <slot />

    <template v-if="!collapsed && !scanning">
      <p
        v-if="providers.data.value && !igdbEnabled"
        class="flex items-start gap-2 text-xs text-muted-foreground"
        data-testid="igdb-note"
      >
        <Info class="mt-px size-3.5 shrink-0" />
        <span>
          {{ t('add.search.igdbDisabled') }}
          <RouterLink :to="{ name: 'integrations' }" class="underline underline-offset-2">
            {{ t('add.search.igdbLink') }}
          </RouterLink>
        </span>
      </p>

      <section v-if="known?.length" class="grid gap-1" data-testid="known-section">
        <h3 class="font-mono text-[11px] tracking-wider text-muted-foreground uppercase">
          {{ t('add.search.known') }}
        </h3>
        <ReleaseRow
          v-for="release in known"
          :key="release.id"
          :release="release"
          @select="emit('release', release)"
        />
      </section>

      <p v-if="isCode" class="text-sm text-muted-foreground" data-testid="code-hint">
        {{ t('add.search.codeHint') }}
      </p>
      <p v-else-if="!ready" class="text-sm text-muted-foreground">
        {{ barcode && !known?.length ? t('add.search.unknownBarcode') : t('add.search.typeMore') }}
      </p>

      <template v-else>
        <section class="grid gap-1" data-testid="catalog-section">
          <h3 class="font-mono text-[11px] tracking-wider text-muted-foreground uppercase">
            {{ t('add.search.catalog') }}
          </h3>
          <div v-if="catalog.isFetching.value && !catalog.data.value" class="py-2">
            <Spinner class="text-muted-foreground" />
          </div>
          <Alert v-else-if="catalog.error.value" variant="destructive">
            <AlertDescription>{{ catalog.error.value.message }}</AlertDescription>
          </Alert>
          <p v-else-if="!catalog.data.value?.length" class="text-sm text-muted-foreground">
            {{ t('add.search.noCatalog') }}
          </p>
          <ReleaseRow
            v-for="release in catalog.data.value ?? []"
            :key="release.id"
            :release="release"
            @select="emit('release', release)"
          />
        </section>

        <section v-if="igdbEnabled" class="grid gap-1" data-testid="provider-section">
          <h3 class="font-mono text-[11px] tracking-wider text-muted-foreground uppercase">
            {{ t('add.search.online') }}
          </h3>
          <div v-if="online.isFetching.value && !online.data.value" class="py-2">
            <Spinner class="text-muted-foreground" />
          </div>
          <Alert v-else-if="online.error.value" variant="destructive">
            <AlertDescription>{{ online.error.value.message }}</AlertDescription>
          </Alert>
          <template v-else-if="online.data.value">
            <p v-if="online.data.value.errors.length" class="text-xs text-muted-foreground">
              {{ t('add.sourceErrors', { sources: online.data.value.errors.join(', ') }) }}
            </p>
            <p v-if="!online.data.value.candidates.length" class="text-sm text-muted-foreground">
              {{ t('add.search.noOnline') }}
            </p>
            <CandidateRow
              v-for="c in online.data.value.candidates"
              :key="`${c.provider}:${c.external_id}:${c.platform_id}`"
              :candidate="c"
              @select="emit('candidate', c)"
            />
          </template>
        </section>
      </template>

      <div
        v-if="(ready || barcode) && auth.canContribute"
        class="flex flex-wrap items-center gap-2 text-sm text-muted-foreground"
      >
        {{ t('add.search.notListed') }}
        <Button
          variant="link"
          size="sm"
          class="h-auto px-0"
          data-testid="to-manual"
          @click="emit('manual', query.trim())"
        >
          <PenLine class="size-3.5" />
          {{ t('add.search.toManual') }}
        </Button>
      </div>
    </template>
  </div>
</template>
