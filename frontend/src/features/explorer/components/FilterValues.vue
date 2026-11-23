<script setup lang="ts">
import { Check } from '@lucide/vue'
import { computed } from 'vue'
import type { GroupField } from '@/api/types'
import { useGroupLabel } from '@/lib/labels'
import { cn } from '@/lib/utils'
import { useTree } from '../composables/useItems'

/** The values a field has in this library (from the tree), as toggles; any may match. */
const props = defineProps<{ libraryId: string; field: GroupField }>()
const selected = defineModel<string[]>({ required: true })
const label = useGroupLabel()
const tree = useTree(
  () => props.libraryId,
  () => ({ groupBy: [props.field], q: '', filters: [], where: [], match: 'all' as const }),
)
const values = computed(() => tree.data.value?.nodes ?? [])

function toggle(key: string) {
  selected.value = selected.value.includes(key)
    ? selected.value.filter((k) => k !== key)
    : [...selected.value, key]
}
</script>

<template>
  <div class="flex flex-wrap gap-1.5" role="group" :data-testid="`filter-values-${field}`">
    <button
      v-for="node in values"
      :key="node.key"
      type="button"
      role="checkbox"
      :aria-checked="selected.includes(node.key)"
      data-testid="filter-value"
      :class="
        cn(
          'inline-flex h-7 items-center gap-1 rounded-md border px-2 text-xs',
          selected.includes(node.key)
            ? 'border-primary bg-primary/10 text-foreground'
            : 'text-muted-foreground hover:bg-muted',
        )
      "
      @click="toggle(node.key)"
    >
      <Check class="size-3" :class="!selected.includes(node.key) && 'invisible'" />
      {{ label(field, node.key, node.label) }}
      <span class="font-mono text-[10px] text-muted-foreground tabular">{{ node.count }}</span>
    </button>
  </div>
</template>
