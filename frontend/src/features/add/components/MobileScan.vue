<script setup lang="ts">
// Adding games on a phone: a large scanner, this round's queue below it and one sheet
// for the decision a code needs. Known codes are added right away; everything returns
// to the scanner. Loaded lazily (only on small screens).
import {
  ArrowLeft,
  BookmarkPlus,
  Check,
  CircleAlert,
  CircleHelp,
  Keyboard,
  ScanBarcode,
  Search,
  SlidersHorizontal,
} from '@lucide/vue'
import { computed, defineAsyncComponent, nextTick, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import type { Candidate, Item, Release, Tracking } from '@/api/types'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Spinner } from '@/components/ui/spinner'
import { Switch } from '@/components/ui/switch'
import { useLocations, usePeople } from '@/features/library/composables/useReference'
import { useUiStore } from '@/stores/ui'
import { nextDetails, type ItemDetails } from '../composables/useItemDetails'
import { entryTitle, useScanRound, type Choice, type ScanEntry } from '../composables/useScanRound'
import ItemDetailsFields from './ItemDetailsFields.vue'
import ItemDetailsForm from './ItemDetailsForm.vue'
import ScanSheet from './ScanSheet.vue'
import SearchTab from './SearchTab.vue'

const CameraScanner = defineAsyncComponent(() => import('./CameraScanner.vue'))

const props = defineProps<{ libraryId: string; active: boolean }>()
const emit = defineEmits<{ manual: [title: string, barcode: string] }>()
const details = defineModel<ItemDetails>('details', { required: true })
const { t } = useI18n()
const ui = useUiStore()
const locations = useLocations(() => props.libraryId)
const people = usePeople(() => props.libraryId)

const round = useScanRound({
  libraryId: () => props.libraryId,
  details,
  autoAdd: () => ui.scanAutoAdd,
  destination: () => ui.addDestination,
})
const { entries } = round

type View =
  | { kind: 'scan' }
  | { kind: 'search'; entry: ScanEntry | null; query: string }
  | { kind: 'defaults' }
  | { kind: 'details'; entry: ScanEntry; release: Release }
const view = ref<View>({ kind: 'scan' })
const typing = ref(false)
const code = ref('')
const codeField = ref<{ $el: HTMLInputElement } | null>(null)
const preparing = ref(false)

/** "Physisch · Regal 2 · Alice": the round's details in one line. */
const summary = computed(() => {
  const d = details.value
  return [
    t(`choices.format.${d.format}`),
    d.status === 'sold' ? t('choices.status.sold') : '',
    locations.data.value?.find((l) => l.id === d.location_id)?.path ?? '',
    people.data.value?.find((p) => p.id === d.owner_id)?.name ?? '',
    d.condition ? t(`choices.condition.${d.condition}`) : '',
  ]
    .filter(Boolean)
    .join(' · ')
})

function onDetect(value: string) {
  if (view.value.kind === 'scan') round.scan(value)
}

async function openCode() {
  typing.value = !typing.value
  if (typing.value) {
    await nextTick()
    codeField.value?.$el.focus()
  }
}

function submitCode() {
  round.scan(code.value)
  code.value = ''
}

function search(entry: ScanEntry | null) {
  const query = entry ? entryTitle(entry) : ''
  round.close()
  view.value = { kind: 'search', entry, query }
}

function picked(choice: Choice) {
  const current = view.value
  round.pick(current.kind === 'search' ? current.entry : null, choice)
  view.value = { kind: 'scan' }
}

function toManual(title: string) {
  const current = view.value
  emit('manual', title, current.kind === 'search' ? (current.entry?.code ?? '') : '')
}

async function toDetails(entry: ScanEntry, choice: Choice, platformId: string) {
  preparing.value = true
  try {
    const release = await round.resolve(entry, choice, platformId)
    entry.release = release
    round.close()
    view.value = { kind: 'details', entry, release }
  } catch (e) {
    entry.error = e instanceof Error ? e.message : t('errors.generic')
  } finally {
    preparing.value = false
  }
}

function fromDetails(result: { item?: Item; tracking?: Tracking }) {
  const current = view.value
  if (current.kind === 'details') round.settle(current.entry, result)
  // Price and notes were for that one copy.
  details.value = nextDetails(details.value)
  view.value = { kind: 'scan' }
}

function stateIcon(entry: ScanEntry) {
  switch (entry.state) {
    case 'added':
      return Check
    case 'tracked':
      return BookmarkPlus
    case 'failed':
      return CircleAlert
    case 'looking':
    case 'review':
    case 'saving':
    case 'unknown':
      return CircleHelp
  }
}

const searchCode = computed(() =>
  view.value.kind === 'search' ? (view.value.entry?.code ?? '') : '',
)
const candidateOf = (c: Candidate): Choice => ({ kind: 'candidate', candidate: c })
const releaseOf = (r: Release): Choice => ({ kind: 'release', release: r })
</script>

<template>
  <div class="relative flex min-h-0 flex-1 flex-col" data-testid="mobile-scan">
    <!-- Scanner, round details and queue. Kept mounted so the camera keeps running. -->
    <div v-show="view.kind === 'scan'" class="flex min-h-0 flex-1 flex-col">
      <div class="grid grid-cols-1 gap-2 px-3 pt-3">
        <CameraScanner v-if="active" @detect="onDetect" />
        <button
          type="button"
          class="flex min-h-10 w-full items-center gap-2 rounded-lg border px-3 py-2 text-left text-sm hover:bg-accent"
          data-testid="round-defaults"
          @click="view = { kind: 'defaults' }"
        >
          <SlidersHorizontal class="size-4 shrink-0 text-muted-foreground" />
          <span class="min-w-0 flex-1 truncate">{{ summary }}</span>
          <span
            v-if="ui.scanAutoAdd"
            class="shrink-0 font-mono text-[11px] tracking-wider text-muted-foreground uppercase"
          >
            {{ t('add.mobile.autoShort') }}
          </span>
        </button>
      </div>

      <div class="flex items-center justify-between px-4 pt-3 pb-1">
        <span class="font-mono text-[11px] tracking-wider text-muted-foreground uppercase">
          {{ t('add.mobile.round') }}
        </span>
        <span class="tabular font-mono text-[11px] text-muted-foreground" data-testid="round-count">
          {{ t('add.mobile.count', { done: round.done.value, all: entries.length }) }}
        </span>
      </div>
      <ul class="min-h-0 flex-1 overflow-y-auto px-3 pb-3" data-testid="queue">
        <li v-if="!entries.length" class="px-1 py-2 text-sm text-muted-foreground">
          {{ t('add.mobile.empty') }}
        </li>
        <li v-for="entry in entries" :key="entry.id">
          <button
            type="button"
            class="flex min-h-11 w-full items-center gap-3 rounded-md px-2 py-1.5 text-left hover:bg-accent"
            data-testid="queue-entry"
            :data-state="entry.state"
            @click="round.open(entry)"
          >
            <span class="min-w-0 flex-1">
              <span v-if="entryTitle(entry)" class="block text-sm font-medium break-words">
                {{ entryTitle(entry) }}
              </span>
              <span
                v-if="entry.code"
                class="block font-mono text-xs text-muted-foreground tabular-nums"
              >
                {{ entry.code }}
              </span>
            </span>
            <Spinner
              v-if="entry.state === 'looking' || entry.state === 'saving'"
              class="text-muted-foreground"
            />
            <component
              :is="stateIcon(entry)"
              v-else
              :class="[
                'size-4 shrink-0',
                entry.state === 'added' || entry.state === 'tracked'
                  ? 'text-success'
                  : entry.state === 'failed'
                    ? 'text-destructive'
                    : 'text-warning',
              ]"
            />
          </button>
        </li>
      </ul>

      <form
        v-if="typing"
        class="flex gap-2 border-t px-3 pt-3"
        data-testid="code-form"
        @submit.prevent="submitCode"
      >
        <Input
          ref="codeField"
          v-model="code"
          autocapitalize="characters"
          spellcheck="false"
          autocomplete="off"
          enterkeyhint="search"
          class="h-10 font-mono tabular-nums"
          :aria-label="t('add.scan.codeLabel')"
          :placeholder="t('add.scan.codePlaceholder')"
          data-testid="mobile-code"
        />
        <Button type="submit" class="h-10" :disabled="!code.trim()">
          <ScanBarcode class="size-4" />
          {{ t('add.scan.lookup') }}
        </Button>
      </form>
      <div class="grid grid-cols-2 gap-2 border-t p-3" :class="{ 'border-t-0': typing }">
        <Button variant="outline" class="h-11" data-testid="open-code" @click="openCode">
          <Keyboard class="size-4" />
          {{ t('add.mobile.code') }}
        </Button>
        <Button variant="outline" class="h-11" data-testid="open-search" @click="search(null)">
          <Search class="size-4" />
          {{ t('add.mobile.searchTitle') }}
        </Button>
      </div>

      <div
        v-if="active && round.active.value"
        class="absolute inset-0 flex flex-col justify-end bg-black/30"
      >
        <ScanSheet
          :key="round.active.value.id"
          :entry="round.active.value"
          :destination-for="round.destinationFor"
          @add="(c, p) => void round.add(round.active.value!, c, p)"
          @details="(c, p) => void toDetails(round.active.value!, c, p)"
          @search="search(round.active.value)"
          @later="round.close()"
          @discard="round.discard(round.active.value!)"
          @retry="void round.retry(round.active.value!)"
          @undo="void round.undo(round.active.value!)"
          @again="void round.again(round.active.value!)"
        />
      </div>
      <div
        v-if="preparing"
        class="absolute inset-0 flex items-center justify-center bg-background/60"
      >
        <Spinner />
      </div>
    </div>

    <!-- Search for a code nothing was found for (or any game). -->
    <div
      v-if="view.kind === 'search'"
      class="flex min-h-0 flex-1 flex-col"
      data-testid="mobile-search"
    >
      <div class="flex items-center gap-2 border-b px-2 py-2">
        <Button
          variant="ghost"
          size="icon"
          :aria-label="t('actions.back')"
          data-testid="search-back"
          @click="view = { kind: 'scan' }"
        >
          <ArrowLeft class="size-4" />
        </Button>
        <span class="text-sm font-medium">{{ t('add.mobile.searchTitle') }}</span>
      </div>
      <div class="min-h-0 flex-1 overflow-y-auto p-3">
        <SearchTab
          :initial-query="view.query"
          :barcode="searchCode || null"
          :known="view.entry?.lookup?.known"
          @release="(r) => picked(releaseOf(r))"
          @candidate="(c) => picked(candidateOf(c))"
          @manual="toManual"
        />
      </div>
    </div>

    <!-- The round's details: every copy of this round gets them. -->
    <div
      v-if="view.kind === 'defaults'"
      class="flex min-h-0 flex-1 flex-col"
      data-testid="mobile-defaults"
    >
      <div class="flex items-center gap-2 border-b px-2 py-2">
        <Button
          variant="ghost"
          size="icon"
          :aria-label="t('actions.back')"
          @click="view = { kind: 'scan' }"
        >
          <ArrowLeft class="size-4" />
        </Button>
        <span class="text-sm font-medium">{{ t('add.mobile.defaults') }}</span>
      </div>
      <div class="grid min-h-0 flex-1 grid-cols-1 content-start gap-4 overflow-y-auto p-4">
        <label class="flex items-start justify-between gap-3 rounded-lg border p-3">
          <span class="grid gap-0.5">
            <span class="text-sm font-medium">{{ t('add.mobile.auto') }}</span>
            <span class="text-xs text-muted-foreground">{{ t('add.mobile.autoText') }}</span>
          </span>
          <Switch v-model="ui.scanAutoAdd" data-testid="auto-add" />
        </label>
        <p class="text-xs text-muted-foreground">{{ t('add.mobile.defaultsText') }}</p>
        <ItemDetailsFields v-model:details="details" :library-id="libraryId" />
      </div>
      <div class="border-t p-3">
        <Button class="h-11 w-full" data-testid="defaults-done" @click="view = { kind: 'scan' }">
          <Check class="size-4" />
          {{ t('add.mobile.done') }}
        </Button>
      </div>
    </div>

    <!-- The full form for one copy (price, notes, Upcoming …). -->
    <div v-if="view.kind === 'details'" class="min-h-0 flex-1 overflow-y-auto p-4">
      <ItemDetailsForm
        v-model:details="details"
        :open="true"
        :release="view.release"
        :library-id="libraryId"
        @created="(item) => fromDetails({ item })"
        @tracked="(tracking) => fromDetails({ tracking })"
        @back="view = { kind: 'scan' }"
      />
    </div>
  </div>
</template>
