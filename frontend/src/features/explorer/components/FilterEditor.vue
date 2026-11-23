<script setup lang="ts">
import { Plus, X } from '@lucide/vue'
import { useQuery } from '@tanstack/vue-query'
import { refDebounced } from '@vueuse/core'
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group'
import {
  formatConditions,
  groupFieldOf,
  isDateField,
  newCondition,
  opsFor,
  type Condition,
} from '@/lib/conditions'
import type { ItemFieldKey } from '@/lib/itemFields'
import FieldCombobox from './FieldCombobox.vue'
import FilterValues from './FilterValues.vue'

/** A view's filters: rows of field · condition · value, all or any of them must hold.
 * Shows live how many copies pass. */
const props = defineProps<{ libraryId: string }>()
const conditions = defineModel<Condition[]>({ required: true })
const match = defineModel<'all' | 'any'>('match', { required: true })
const { t } = useI18n()

function update(index: number, patch: Partial<Condition>) {
  conditions.value = conditions.value.map((c, i) => (i === index ? { ...c, ...patch } : c))
}
function setField(index: number, field: ItemFieldKey) {
  conditions.value = conditions.value.map((c, i) => (i === index ? newCondition(field) : c))
}
function remove(index: number) {
  conditions.value = conditions.value.filter((_, i) => i !== index)
}
const placeholder = (c: Condition) =>
  c.op === 'match' || c.op === 'not_match' ? t('explorer.patternHint') : ''

// Live count: how many copies these filters let through (debounced while typing).
const where = refDebounced(
  computed(() => formatConditions(conditions.value)),
  300,
)
const count = (filters: string[], mode: 'all' | 'any') =>
  unwrap(
    api.GET('/api/libraries/{library_id}/items', {
      params: {
        path: { library_id: props.libraryId },
        query: { where: filters, match: mode, limit: 1 },
      },
    }),
  ).then((page) => page.count)
const passing = useQuery({
  queryKey: computed(() => ['items', props.libraryId, 'count', where.value, match.value]),
  queryFn: () => count(where.value, match.value),
})
const total = useQuery({
  queryKey: computed(() => ['items', props.libraryId, 'count']),
  queryFn: () => count([], 'all'),
})
</script>

<template>
  <div class="grid gap-3" data-testid="filter-editor">
    <ToggleGroup
      v-if="conditions.length > 1"
      :model-value="match"
      type="single"
      variant="outline"
      size="sm"
      class="justify-self-start"
      data-testid="filter-match"
      @update:model-value="(v) => v && (match = v as 'all' | 'any')"
    >
      <ToggleGroupItem value="all" data-testid="match-all">{{
        t('explorer.matchAll')
      }}</ToggleGroupItem>
      <ToggleGroupItem value="any" data-testid="match-any">{{
        t('explorer.matchAny')
      }}</ToggleGroupItem>
    </ToggleGroup>

    <div
      v-for="(condition, index) in conditions"
      :key="index"
      class="grid gap-2 rounded-lg border bg-card p-3"
      :data-testid="`filter-${index}`"
    >
      <div class="flex items-center gap-2">
        <FieldCombobox
          :id="`filter-${index}`"
          :model-value="condition.field"
          @update:model-value="(field) => setField(index, field)"
        />
        <select
          :value="condition.op"
          class="h-8 min-w-0 flex-1 rounded-lg border bg-transparent px-2 text-sm dark:bg-input/30"
          :aria-label="t('explorer.filterOp')"
          data-testid="filter-op"
          @change="
            update(index, {
              op: ($event.target as HTMLSelectElement).value as Condition['op'],
            })
          "
        >
          <option v-for="op in opsFor(condition.field)" :key="op" :value="op">
            {{ t(`explorer.ops.${op}`) }}
          </option>
        </select>
        <Button
          type="button"
          variant="ghost"
          size="icon-sm"
          class="shrink-0"
          :aria-label="t('explorer.removeFilter')"
          data-testid="remove-filter"
          @click="remove(index)"
        >
          <X class="size-4" />
        </Button>
      </div>
      <div
        v-if="['match', 'not_match', 'gte', 'lte', 'between'].includes(condition.op)"
        class="flex items-center gap-2"
      >
        <Input
          :model-value="condition.text"
          :type="
            isDateField(condition.field)
              ? 'date'
              : condition.op.endsWith('match')
                ? 'text'
                : 'number'
          "
          class="h-8 min-w-0 flex-1"
          :placeholder="placeholder(condition)"
          :aria-label="t('explorer.filterValue')"
          data-testid="filter-text"
          @update:model-value="(v) => update(index, { text: String(v) })"
        />
        <template v-if="condition.op === 'between'">
          <span class="text-xs text-muted-foreground">{{ t('explorer.and') }}</span>
          <Input
            :model-value="condition.high"
            :type="isDateField(condition.field) ? 'date' : 'number'"
            class="h-8 min-w-0 flex-1"
            :aria-label="t('explorer.filterHigh')"
            data-testid="filter-high"
            @update:model-value="(v) => update(index, { high: String(v) })"
          />
        </template>
      </div>
      <FilterValues
        v-if="(condition.op === 'in' || condition.op === 'not_in') && groupFieldOf(condition.field)"
        :library-id="props.libraryId"
        :field="groupFieldOf(condition.field)!"
        :model-value="condition.values"
        @update:model-value="(values) => update(index, { values })"
      />
    </div>

    <div class="flex flex-wrap items-center gap-3">
      <Button
        type="button"
        variant="outline"
        size="sm"
        data-testid="add-filter"
        @click="conditions = [...conditions, newCondition()]"
      >
        <Plus class="size-4" /> {{ t('explorer.addFilter') }}
      </Button>
      <span
        v-if="passing.data.value !== undefined && total.data.value !== undefined"
        class="font-mono text-xs text-muted-foreground tabular"
        data-testid="filter-count"
      >
        {{ t('explorer.filterCount', { n: passing.data.value, total: total.data.value }) }}
      </span>
    </div>
  </div>
</template>
