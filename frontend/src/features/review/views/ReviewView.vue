<script setup lang="ts">
// Admins check what people entered themselves: games and releases typed in by hand and
// barcodes assigned while adding. Everything is usable already; approving only marks it.
import { Barcode, Check, Disc3, Gamepad2, Trash2 } from '@lucide/vue'
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import type { components } from '@/api/schema'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Spinner } from '@/components/ui/spinner'
import { useReviewActions, useReviewQueue } from '../composables/useReview'

type Entry = components['schemas']['ReviewEntryOut']

const { t, d } = useI18n()
const queue = useReviewQueue()
const { approve, removeBarcode } = useReviewActions()
const entries = computed(() => queue.data.value?.entries ?? [])
const ICONS = { work: Gamepad2, release: Disc3, barcode: Barcode }

function approveOne(entry: Entry) {
  const key = `${entry.kind}s`
  approve.mutate({ [key]: [entry.id] })
}

function approveAll() {
  const pick = (kind: Entry['kind']) =>
    entries.value.filter((e) => e.kind === kind).map((e) => e.id)
  approve.mutate({ works: pick('work'), releases: pick('release'), barcodes: pick('barcode') })
}

const link = (entry: Entry) =>
  entry.release_id
    ? { name: 'release', params: { releaseId: entry.release_id } }
    : { name: 'work', params: { workId: entry.work_id } }
</script>

<template>
  <div class="flex min-w-0 flex-1 flex-col" data-testid="review-view">
    <header class="flex flex-wrap items-center justify-between gap-3 border-b px-4 py-3 md:px-6">
      <div class="min-w-0">
        <h1 class="text-lg font-semibold tracking-tight">{{ t('review.title') }}</h1>
        <p class="text-sm text-muted-foreground">{{ t('review.subtitle') }}</p>
      </div>
      <Button
        v-if="entries.length > 1"
        :disabled="approve.isPending.value"
        data-testid="approve-all"
        @click="approveAll"
      >
        <Check /> {{ t('review.approveAll') }}
      </Button>
    </header>

    <div class="grid max-w-4xl gap-3 p-4 md:px-6">
      <div v-if="queue.isPending.value" class="flex justify-center py-10">
        <Spinner class="size-6" />
      </div>
      <Alert v-else-if="queue.isError.value" variant="destructive">
        <AlertDescription>{{ queue.error.value?.message }}</AlertDescription>
      </Alert>
      <p
        v-else-if="!entries.length"
        class="text-sm text-muted-foreground"
        data-testid="review-empty"
      >
        {{ t('review.empty') }}
      </p>
      <Alert v-if="approve.error.value || removeBarcode.error.value" variant="destructive">
        <AlertDescription>
          {{ (approve.error.value ?? removeBarcode.error.value)?.message }}
        </AlertDescription>
      </Alert>
      <ul v-if="entries.length" class="divide-y rounded-lg border bg-card">
        <li
          v-for="entry in entries"
          :key="`${entry.kind}:${entry.id}`"
          class="flex flex-wrap items-center gap-3 px-3 py-2.5"
          data-testid="review-entry"
        >
          <component :is="ICONS[entry.kind]" class="size-4 shrink-0 text-muted-foreground" />
          <div class="min-w-0 flex-1">
            <RouterLink :to="link(entry)" class="font-medium break-words hover:underline">
              {{ entry.title }}
            </RouterLink>
            <p class="text-xs break-words text-muted-foreground">
              <span class="font-mono text-[11px] tracking-wider uppercase">
                {{ t(`review.kinds.${entry.kind}`) }}
              </span>
              <template v-if="entry.detail"> · {{ entry.detail }}</template>
            </p>
            <p class="tabular font-mono text-[11px] text-muted-foreground">
              {{ entry.created_by ?? t('review.unknown') }} ·
              {{ d(new Date(entry.created_at), 'short') }} ·
              {{ t('review.copies', { n: entry.copies }, entry.copies) }}
            </p>
          </div>
          <div class="flex shrink-0 gap-1.5">
            <Button
              v-if="entry.kind === 'barcode'"
              variant="ghost"
              size="sm"
              :disabled="removeBarcode.isPending.value"
              data-testid="remove-barcode"
              @click="removeBarcode.mutate(entry.id)"
            >
              <Trash2 class="size-3.5" /> {{ t('review.removeBarcode') }}
            </Button>
            <Button
              variant="outline"
              size="sm"
              :disabled="approve.isPending.value"
              data-testid="approve"
              @click="approveOne(entry)"
            >
              <Check class="size-3.5" /> {{ t('review.approve') }}
            </Button>
          </div>
        </li>
      </ul>
      <p v-if="entries.length" class="text-xs text-muted-foreground">{{ t('review.hint') }}</p>
    </div>
  </div>
</template>
