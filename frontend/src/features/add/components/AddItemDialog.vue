<script setup lang="ts">
import { useMediaQuery } from '@vueuse/core'
import { computed, defineAsyncComponent, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { toast } from 'vue-sonner'
import type { Candidate, Item, Release, Tracking } from '@/api/types'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Spinner } from '@/components/ui/spinner'
import { useUiStore } from '@/stores/ui'
import { ApiError } from '@/api/errors'
import { attachBarcode, lookupBarcode } from '../composables/useAddApi'
import { emptyDetails, nextDetails } from '../composables/useItemDetails'
import CandidateConfirm from './CandidateConfirm.vue'
import ItemDetailsForm from './ItemDetailsForm.vue'
import SearchTab from './SearchTab.vue'

// Phones get their own scanning view (large camera, queue, one sheet per decision).
const MobileScan = defineAsyncComponent(() => import('./MobileScan.vue'))
const CameraScanner = defineAsyncComponent(() => import('./CameraScanner.vue'))

type Step =
  | { kind: 'browse' }
  | { kind: 'candidate'; candidate: Candidate; barcode: string | null }
  | { kind: 'item'; release: Release }

const { t } = useI18n()
const ui = useUiStore()
const router = useRouter()

const scanning = ref(false)
const looking = ref(false)
const lookingCode = ref('')
const scanError = ref('')
let request = 0
const step = ref<Step>({ kind: 'browse' })
const added = ref(0)
const details = ref(emptyDetails())
const moreOpen = ref(false)
// A scanned code: kept while searching by title, so the game picked there gets the
// barcode and the next scan finds it.
const searchBarcode = ref<string | null>(null)
const searchKnown = ref<Release[]>([])
// Remounts the search: an empty field for the next game.
const searchKey = ref(0)
const roundKey = ref(0)

const compact = useMediaQuery('(max-width: 639.98px)')
const phoneScan = computed(() => compact.value && scanning.value && step.value.kind === 'browse')

const libraryId = computed(() => ui.addLibraryId ?? '')

function reset() {
  scanning.value = ui.addMode === 'scan'
  scanError.value = ''
  step.value = { kind: 'browse' }
  added.value = 0
  details.value = emptyDetails()
  clearSearch()
  roundKey.value++
}

function clearSearch() {
  searchBarcode.value = null
  searchKnown.value = []
  searchKey.value++
}

watch(
  () => ui.addOpen,
  (open) => open && reset(),
  { immediate: true },
)

/** Tapping a toast (e.g. "Undo") is not a click outside that should close the dialog. */
function keepForToasts(event: Event) {
  const target = event.target
  if (target instanceof Element && target.closest('[data-sonner-toaster]')) event.preventDefault()
}

/** Back from a picked game to the results, as soon as the search changes. */
function onTyping() {
  scanning.value = false
  scanError.value = ''
  step.value = { kind: 'browse' }
}

function toggleScan() {
  scanning.value = !scanning.value
  scanError.value = ''
  step.value = { kind: 'browse' }
}

function clearBarcode() {
  searchBarcode.value = null
  searchKnown.value = []
}

/** A code from the camera or the field: on to the search with it. A misread stays here. */
async function lookup(raw: string) {
  const code = raw.replace(/\s+/g, '')
  const current = ++request
  lookingCode.value = code
  looking.value = true
  scanError.value = ''
  try {
    const found = await lookupBarcode(code)
    if (current !== request) return
    searchBarcode.value = found.code
    searchKnown.value = found.known
    searchKey.value++
    scanning.value = false
    step.value = { kind: 'browse' }
  } catch (e) {
    if (current === request)
      scanError.value = e instanceof ApiError ? e.message : t('errors.generic')
  } finally {
    if (current === request) looking.value = false
  }
}

function chooseRelease(release: Release) {
  step.value = { kind: 'item', release }
}

/** A catalog release picked in the search after a scan gets that barcode. */
async function chooseSearchedRelease(release: Release) {
  const code = searchBarcode.value
  if (code && !release.barcodes.includes(code)) {
    try {
      release = await attachBarcode(release.id, code)
      searchBarcode.value = null
    } catch (e) {
      const message = e instanceof ApiError ? e.message : t('errors.generic')
      toast.error(t('add.search.barcodeFailed', { message }))
    }
  }
  chooseRelease(release)
}

function chooseCandidate(candidate: Candidate, barcode: string | null) {
  step.value = { kind: 'candidate', candidate, barcode }
}

function toManual(title: string, barcode: string) {
  ui.addOpen = false
  void router.push({
    name: 'release-new',
    query: { ...(title && { title }), ...(barcode && { barcode }) },
  })
}

function onCreated(item: Item, next: boolean) {
  added.value++
  toast.success(t('add.added', { title: item.title }))
  if (next) {
    details.value = nextDetails(details.value)
    step.value = { kind: 'browse' }
    scanning.value = true
    clearSearch()
    return
  }
  const id = libraryId.value
  ui.addOpen = false
  void router.push({ name: 'explorer', params: { libraryId: id }, query: { item: item.id } })
}

function onTracked(entry: Tracking) {
  toast.success(t('add.track.done', { title: entry.release.title }))
  ui.addOpen = false
  void router.push({ name: 'upcoming' })
}
</script>

<template>
  <Dialog v-model:open="ui.addOpen">
    <DialogContent
      data-testid="add-dialog"
      @interact-outside="keepForToasts"
      @open-auto-focus="(e: Event) => scanning && e.preventDefault()"
      class="flex h-dvh max-h-dvh w-full max-w-full flex-col gap-0 overflow-hidden rounded-none p-0 sm:h-[min(85dvh,40rem)] sm:max-w-3xl sm:rounded-xl"
    >
      <DialogHeader class="border-b px-4 py-3 pr-12 text-left">
        <DialogTitle class="text-base font-semibold tracking-tight">
          {{ t('add.title') }}
        </DialogTitle>
        <DialogDescription :class="['text-xs', phoneScan && 'sr-only']">
          <span v-if="added" class="font-mono tabular-nums" data-testid="added-count">
            {{ t('add.addedCount', { n: added }, added) }}
          </span>
          <span v-else>{{ t('add.description') }}</span>
        </DialogDescription>
      </DialogHeader>

      <MobileScan
        v-if="compact && ui.addOpen"
        v-show="phoneScan"
        :key="roundKey"
        v-model:details="details"
        :library-id="libraryId"
        :active="phoneScan"
        @manual="toManual"
      />
      <div
        v-show="!phoneScan"
        class="min-h-0 flex-1 overflow-y-auto px-4 pb-4 [scrollbar-gutter:stable]"
      >
        <SearchTab
          :key="searchKey"
          scannable
          :barcode="searchBarcode"
          :known="searchKnown"
          :scanning="scanning"
          :collapsed="step.kind !== 'browse'"
          @typing="onTyping"
          @code="lookup"
          @toggle-scan="toggleScan"
          @clear-barcode="clearBarcode"
          @release="chooseSearchedRelease"
          @candidate="(c) => chooseCandidate(c, searchBarcode)"
          @manual="(title) => toManual(title, searchBarcode ?? '')"
        >
          <CameraScanner v-if="scanning && !compact && ui.addOpen" @detect="lookup" />
          <div v-if="looking" class="flex items-center gap-2 text-sm text-muted-foreground">
            <Spinner />
            {{ t('add.scan.looking', { code: lookingCode }) }}
          </div>
          <Alert v-else-if="scanError" variant="destructive" data-testid="scan-error">
            <AlertDescription>{{ scanError }}</AlertDescription>
          </Alert>
        </SearchTab>

        <CandidateConfirm
          v-if="step.kind === 'candidate'"
          class="mt-4"
          :candidate="step.candidate"
          :barcode="step.barcode"
          @imported="chooseRelease"
          @back="step = { kind: 'browse' }"
        />

        <ItemDetailsForm
          v-else-if="step.kind === 'item'"
          v-model:details="details"
          v-model:open="moreOpen"
          class="mt-4"
          :release="step.release"
          :library-id="libraryId"
          @created="onCreated"
          @tracked="onTracked"
          @back="step = { kind: 'browse' }"
        />
      </div>
    </DialogContent>
  </Dialog>
</template>
