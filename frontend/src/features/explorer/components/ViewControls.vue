<script setup lang="ts">
import { LayoutGrid, List, PanelRight, Sheet } from '@lucide/vue'
import { useI18n } from 'vue-i18n'
import { Button } from '@/components/ui/button'
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group'
import type { GroupField } from '@/api/types'
import type { SortLevel, ViewFields } from '@/lib/itemFields'
import type { GridSize } from '@/stores/ui'
import type { Layout } from '../composables/useExplorerState'
import FieldsDialog from './FieldsDialog.vue'
import SectionPicker from './SectionPicker.vue'
import SortDialog from './SortDialog.vue'

defineProps<{
  sort: SortLevel[]
  layout: Layout
  section: GroupField | ''
  /** Whether all sections are folded in; null without sections. */
  allCollapsed: boolean | null
  gridSize: GridSize
  detailPane: boolean
  fields: ViewFields
}>()
const emit = defineEmits<{
  sort: [levels: SortLevel[]]
  layout: [value: Layout]
  gridSize: [value: GridSize]
  detailPane: [value: boolean]
  fields: [value: ViewFields]
  section: [value: GroupField | '']
  toggleAll: []
}>()
const { t } = useI18n()
const layouts = [
  { value: 'grid', icon: LayoutGrid },
  { value: 'list', icon: List },
  { value: 'table', icon: Sheet },
] as const
const sizes: GridSize[] = ['s', 'm', 'l']
</script>

<template>
  <div class="flex flex-wrap items-center gap-1.5">
    <FieldsDialog
      :model-value="fields"
      :initial="layout"
      @update:model-value="emit('fields', $event)"
    />
    <SortDialog :model-value="sort" @update:model-value="emit('sort', $event)" />
    <SectionPicker
      :model-value="section"
      :all-collapsed="allCollapsed"
      @update:model-value="emit('section', $event)"
      @toggle-all="emit('toggleAll')"
    />
    <ToggleGroup
      type="single"
      variant="outline"
      size="sm"
      :model-value="layout"
      @update:model-value="(v) => v && emit('layout', v as Layout)"
    >
      <ToggleGroupItem
        v-for="l in layouts"
        :key="l.value"
        :value="l.value"
        :aria-label="t(`choices.layout.${l.value}`)"
        :data-testid="`layout-${l.value}`"
      >
        <component :is="l.icon" class="size-4" />
      </ToggleGroupItem>
    </ToggleGroup>
    <ToggleGroup
      v-if="layout === 'grid'"
      type="single"
      variant="outline"
      size="sm"
      :aria-label="t('explorer.coverSize')"
      :model-value="gridSize"
      @update:model-value="(v) => v && emit('gridSize', v as GridSize)"
    >
      <ToggleGroupItem
        v-for="s in sizes"
        :key="s"
        :value="s"
        :aria-label="`${t('explorer.coverSize')} ${s.toUpperCase()}`"
        :data-testid="`grid-${s}`"
        class="font-mono text-[11px] uppercase"
      >
        {{ s }}
      </ToggleGroupItem>
    </ToggleGroup>
    <Button
      variant="outline"
      size="icon-sm"
      class="hidden lg:inline-flex"
      :class="detailPane && 'border-primary bg-primary/10 text-primary'"
      :aria-label="t('explorer.detailPane')"
      :title="t('explorer.detailPane')"
      :aria-pressed="detailPane"
      data-testid="toggle-detail-pane"
      @click="emit('detailPane', !detailPane)"
    >
      <PanelRight class="size-4" />
    </Button>
  </div>
</template>
