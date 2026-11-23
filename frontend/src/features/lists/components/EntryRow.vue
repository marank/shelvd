<script setup lang="ts">
import { ArrowDown, ArrowUp, X } from '@lucide/vue'
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import type { ListEntry } from '@/api/types'
import CoverImage from '@/components/app/CoverImage.vue'
import PlatformBadge from '@/components/app/PlatformBadge.vue'
import ReleaseDate from '@/components/app/ReleaseDate.vue'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'

/** One game on a list: cover, title, editable note, reorder and remove controls. */
const props = defineProps<{
  entry: ListEntry
  index: number
  first: boolean
  last: boolean
  busy?: boolean
}>()
const emit = defineEmits<{ move: [delta: -1 | 1]; remove: []; note: [note: string] }>()
const { t } = useI18n()

const note = ref(props.entry.note)
watch(
  () => props.entry.note,
  (value) => (note.value = value),
)

function saveNote() {
  const value = note.value.trim()
  if (value !== props.entry.note) emit('note', value)
}
</script>

<template>
  <li class="flex items-start gap-3 py-3" data-testid="entry">
    <span class="w-5 shrink-0 pt-1 text-right font-mono text-xs text-muted-foreground tabular">
      {{ index + 1 }}
    </span>
    <CoverImage
      fit="box"
      :src="entry.release.cover_url"
      :title="entry.release.title"
      :manufacturer="entry.release.platform.manufacturer"
      class="w-10 shrink-0"
    />
    <div class="grid min-w-0 flex-1 gap-1.5">
      <div class="flex flex-wrap items-center gap-x-2 gap-y-1">
        <span class="min-w-0 truncate font-medium">{{ entry.release.title }}</span>
        <PlatformBadge :platform="entry.release.platform" />
        <ReleaseDate
          :release="entry.release"
          class="text-xs text-muted-foreground"
          data-testid="entry-date"
        />
      </div>
      <Input
        v-model="note"
        data-testid="entry-note"
        class="h-7 border-transparent bg-transparent px-1.5 text-sm shadow-none hover:border-input focus-visible:border-ring"
        :placeholder="t('lists.notePlaceholder')"
        :aria-label="t('lists.note')"
        @blur="saveNote"
        @keydown.enter.prevent="($event.target as HTMLInputElement).blur()"
      />
    </div>
    <div class="flex shrink-0 items-center gap-0.5">
      <Button
        variant="ghost"
        size="icon-sm"
        data-testid="move-up"
        :disabled="first || busy"
        :aria-label="t('lists.moveUp')"
        :title="t('lists.moveUp')"
        @click="emit('move', -1)"
      >
        <ArrowUp />
      </Button>
      <Button
        variant="ghost"
        size="icon-sm"
        data-testid="move-down"
        :disabled="last || busy"
        :aria-label="t('lists.moveDown')"
        :title="t('lists.moveDown')"
        @click="emit('move', 1)"
      >
        <ArrowDown />
      </Button>
      <Button
        variant="ghost"
        size="icon-sm"
        data-testid="remove-entry"
        :disabled="busy"
        :aria-label="t('lists.remove')"
        :title="t('lists.remove')"
        @click="emit('remove')"
      >
        <X />
      </Button>
    </div>
  </li>
</template>
