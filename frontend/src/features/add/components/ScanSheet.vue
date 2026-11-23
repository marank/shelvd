<script setup lang="ts">
// The decision for one entry of the scanning round, as a sheet over the queue.
import {
  BookmarkPlus,
  Check,
  Copy,
  PenLine,
  RotateCcw,
  ScanBarcode,
  Search,
  Trash2,
  Undo2,
  X,
} from '@lucide/vue'
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import type { Release } from '@/api/types'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Spinner } from '@/components/ui/spinner'
import NativeSelect from '@/components/app/NativeSelect.vue'
import { usePlatforms } from '@/features/library/composables/useReference'
import { cn } from '@/lib/utils'
import type { AddDestination } from '@/stores/ui'
import { choicesOf, entryTitle, type Choice, type ScanEntry } from '../composables/useScanRound'
import CandidateRow from './CandidateRow.vue'
import ReleaseRow from './ReleaseRow.vue'

const props = defineProps<{
  entry: ScanEntry
  destinationFor: (release: Release) => AddDestination
}>()
const emit = defineEmits<{
  add: [choice: Choice, platformId: string]
  details: [choice: Choice, platformId: string]
  search: []
  later: []
  discard: []
  retry: []
  undo: []
  again: []
}>()
const { t } = useI18n()
const platforms = usePlatforms()

const choices = computed(() => choicesOf(props.entry))
const selected = ref(0)
const choice = computed(() => choices.value[selected.value] ?? choices.value[0] ?? null)
const platformId = ref('')
watch(
  () => [props.entry.id, choices.value.length] as const,
  () => {
    selected.value = 0
  },
)
watch(
  choice,
  (c) => {
    platformId.value = c?.kind === 'candidate' ? (c.candidate.platform_id ?? '') : ''
  },
  { immediate: true },
)
const needsPlatform = computed(() => choice.value?.kind === 'candidate' && !platformId.value)
const tracks = computed(
  () => choice.value?.kind === 'release' && props.destinationFor(choice.value.release) === 'track',
)
const saving = computed(() => props.entry.state === 'saving')
/** Adding one more of something already in the library. */
const another = computed(
  () => choice.value?.kind === 'release' && choice.value.release.id === props.entry.duplicateOf,
)

function key(c: Choice): string {
  return c.kind === 'release'
    ? `r:${c.release.id}`
    : `c:${c.candidate.provider}:${c.candidate.external_id}:${c.candidate.platform_id}`
}
</script>

<template>
  <section
    class="grid max-h-[75%] grid-cols-1 gap-3 overflow-y-auto rounded-t-2xl border-t bg-background p-4 shadow-[0_-8px_24px_rgb(0_0_0/0.25)]"
    data-testid="scan-sheet"
    :aria-label="t('add.mobile.sheet')"
  >
    <header class="flex items-start justify-between gap-2">
      <div class="min-w-0">
        <p v-if="entry.code" class="font-mono text-xs text-muted-foreground tabular-nums">
          <ScanBarcode class="mr-1 inline size-3.5 align-[-2px]" />{{ entry.code }}
        </p>
        <p v-if="entry.state === 'unknown'" class="font-medium" data-testid="sheet-unknown">
          {{ t('add.mobile.unknown') }}
        </p>
        <p v-else-if="entry.state === 'failed'" class="font-medium">
          {{ t('add.mobile.failed') }}
        </p>
        <p
          v-else-if="entry.state === 'added' || entry.state === 'tracked'"
          class="font-medium break-words"
        >
          {{
            entry.state === 'added'
              ? t('add.added', { title: entryTitle(entry) })
              : t('add.track.done', { title: entryTitle(entry) })
          }}
        </p>
        <p v-else-if="entry.duplicateOf" class="font-medium" data-testid="sheet-duplicate">
          {{ t('add.mobile.duplicate') }}
        </p>
        <p v-else-if="choices.length > 1" class="font-medium">
          {{ t('add.mobile.pick', { n: choices.length }) }}
        </p>
      </div>
      <Button
        variant="ghost"
        size="icon-sm"
        class="-mt-1 -mr-2 shrink-0"
        :aria-label="t('add.mobile.later')"
        data-testid="sheet-close"
        @click="emit('later')"
      >
        <X class="size-4" />
      </Button>
    </header>

    <div
      v-if="entry.state === 'looking'"
      class="flex items-center gap-2 text-sm text-muted-foreground"
    >
      <Spinner />
      {{ t('add.scan.looking', { code: entry.code }) }}
    </div>

    <!-- Nothing found: search, keep for later or drop it. -->
    <template v-else-if="entry.state === 'unknown'">
      <Button size="lg" class="h-11" data-testid="sheet-search" @click="emit('search')">
        <Search class="size-4" />
        {{ t('add.mobile.search') }}
      </Button>
      <div class="grid grid-cols-2 gap-2">
        <Button variant="outline" class="h-10" data-testid="sheet-later" @click="emit('later')">
          {{ t('add.mobile.later') }}
        </Button>
        <Button variant="outline" class="h-10" data-testid="sheet-discard" @click="emit('discard')">
          <Trash2 class="size-4" />
          {{ t('add.mobile.discard') }}
        </Button>
      </div>
    </template>

    <template v-else-if="entry.state === 'failed'">
      <Alert variant="destructive">
        <AlertDescription>{{ entry.error }}</AlertDescription>
      </Alert>
      <div class="grid grid-cols-2 gap-2">
        <Button class="h-10" data-testid="sheet-retry" @click="emit('retry')">
          <RotateCcw class="size-4" />
          {{ t('actions.retry') }}
        </Button>
        <Button variant="outline" class="h-10" data-testid="sheet-discard" @click="emit('discard')">
          <Trash2 class="size-4" />
          {{ t('add.mobile.discard') }}
        </Button>
      </div>
    </template>

    <!-- Done: undo, or another copy of the same game. -->
    <template v-else-if="entry.state === 'added' || entry.state === 'tracked'">
      <Alert v-if="entry.error" variant="destructive" data-testid="sheet-error">
        <AlertDescription>{{ entry.error }}</AlertDescription>
      </Alert>
      <div class="grid grid-cols-2 gap-2">
        <Button variant="outline" class="h-10" data-testid="sheet-undo" @click="emit('undo')">
          <Undo2 class="size-4" />
          {{ t('add.mobile.undo') }}
        </Button>
        <Button
          v-if="entry.state === 'added'"
          variant="outline"
          class="h-10"
          data-testid="sheet-again"
          @click="emit('again')"
        >
          <Copy class="size-4" />
          {{ t('add.mobile.again') }}
        </Button>
      </div>
    </template>

    <!-- Options: one tap adds the selected one. -->
    <template v-else-if="choice">
      <div class="grid grid-cols-1 gap-1" role="radiogroup" :aria-label="t('add.mobile.sheet')">
        <div
          v-for="(c, i) in choices"
          :key="key(c)"
          role="radio"
          :aria-checked="i === selected"
          :class="
            cn(
              'rounded-lg border',
              i === selected ? 'border-primary bg-primary/5' : 'border-transparent',
            )
          "
        >
          <ReleaseRow v-if="c.kind === 'release'" :release="c.release" @select="selected = i" />
          <CandidateRow v-else :candidate="c.candidate" @select="selected = i" />
        </div>
      </div>

      <div v-if="choice.kind === 'candidate' && !choice.candidate.platform_id" class="grid gap-1.5">
        <label for="sheet-platform" class="text-sm font-medium">{{ t('fields.platform') }} *</label>
        <NativeSelect id="sheet-platform" v-model="platformId" required>
          <option value="" disabled>{{ t('add.choose') }}</option>
          <option v-for="p in platforms.data.value ?? []" :key="p.id" :value="p.id">
            {{ p.name }}
          </option>
        </NativeSelect>
      </div>

      <Alert v-if="entry.error" variant="destructive" data-testid="sheet-error">
        <AlertDescription>{{ entry.error }}</AlertDescription>
      </Alert>

      <Button
        size="lg"
        class="h-11"
        :disabled="saving || needsPlatform"
        data-testid="sheet-add"
        @click="emit('add', choice, platformId)"
      >
        <Spinner v-if="saving" />
        <BookmarkPlus v-else-if="tracks" class="size-4" />
        <Copy v-else-if="another" class="size-4" />
        <Check v-else class="size-4" />
        {{ tracks ? t('add.mobile.track') : another ? t('add.mobile.again') : t('add.mobile.add') }}
      </Button>
      <div class="grid grid-cols-2 gap-2">
        <Button
          variant="outline"
          class="h-10"
          :disabled="saving"
          data-testid="sheet-other"
          @click="emit('search')"
        >
          <Search class="size-4" />
          {{ t('add.mobile.other') }}
        </Button>
        <Button
          variant="outline"
          class="h-10"
          :disabled="saving || needsPlatform"
          data-testid="sheet-details"
          @click="emit('details', choice, platformId)"
        >
          <PenLine class="size-4" />
          {{ t('add.mobile.details') }}
        </Button>
      </div>
      <Button
        variant="ghost"
        :disabled="saving"
        class="text-muted-foreground"
        data-testid="sheet-discard"
        @click="emit('discard')"
      >
        <Trash2 class="size-4" />
        {{ t('add.mobile.discard') }}
      </Button>
    </template>
  </section>
</template>
