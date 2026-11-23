<script setup lang="ts">
import { X } from '@lucide/vue'
import LevelLink from '@/components/app/LevelLink.vue'
import { defineAsyncComponent } from 'vue'
import { useI18n } from 'vue-i18n'
import ResizeHandle from '@/components/app/ResizeHandle.vue'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { useItem } from '@/features/items/composables/useItem'
import type { ItemFieldKey } from '@/lib/itemFields'
import { DETAIL_DEFAULT, useUiStore } from '@/stores/ui'

/** Third column of the explorer: the selected copy, its release and game, resizable. */
// Only needed once a copy is selected: not part of the first load.
const CopyColumn = defineAsyncComponent(() => import('./CopyColumn.vue'))
const props = defineProps<{ libraryId: string; itemId: string; fields?: ItemFieldKey[] }>()
const emit = defineEmits<{ close: [] }>()
const { t } = useI18n()
const ui = useUiStore()
const item = useItem(
  () => props.libraryId,
  () => props.itemId,
)
</script>

<template>
  <aside
    class="relative flex min-h-0 shrink-0 flex-col border-l bg-background"
    :style="{ width: `${ui.detailWidth}px` }"
    data-testid="detail-pane"
    :aria-label="t('works.details')"
  >
    <ResizeHandle
      v-model="ui.detailWidth"
      edge="left"
      :min="340"
      :max="900"
      :default-width="DETAIL_DEFAULT"
      :label="t('layout.resizeDetails')"
    />
    <div class="flex h-10 shrink-0 items-center gap-1 border-b px-3">
      <span class="min-w-0 flex-1 truncate font-mono text-[11px] text-muted-foreground">
        {{ t('explorer.keyboardHint') }}
      </span>
      <!-- The selection is a copy: its page is the "full page"; game and release
           open from their blocks below. -->
      <LevelLink v-if="item.data.value" level="item" :to="{ name: 'item', params: { itemId } }" />
      <Button
        variant="ghost"
        size="icon-sm"
        :aria-label="t('explorer.closeDetails')"
        :title="t('explorer.closeDetails')"
        data-testid="close-details"
        @click="emit('close')"
      >
        <X class="size-4" />
      </Button>
    </div>
    <div class="min-h-0 flex-1 overflow-y-auto p-4">
      <CopyColumn
        v-if="item.data.value"
        :library-id="libraryId"
        :item="item.data.value"
        :fields="fields"
        @close="emit('close')"
      />
      <div v-else class="space-y-3">
        <Skeleton class="mx-auto aspect-[5/7] h-80" />
        <Skeleton class="h-6 w-2/3" />
      </div>
    </div>
  </aside>
</template>
