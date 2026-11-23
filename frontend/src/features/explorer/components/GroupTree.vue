<script setup lang="ts">
import { ChevronRight } from '@lucide/vue'
import { computed, ref, watch } from 'vue'
import type { GroupNode } from '@/api/types'
import { useGroupLabel } from '@/lib/labels'
import { cn } from '@/lib/utils'

defineOptions({ name: 'GroupTree' })

const props = defineProps<{
  nodes: GroupNode[]
  /** Keys of the parent levels, so each node knows its full path. */
  prefix?: string[]
  /** The currently open path. */
  active: string[]
  depth?: number
}>()
const emit = defineEmits<{ open: [path: string[]] }>()

const label = useGroupLabel()
const level = computed(() => props.depth ?? 0)
const base = computed(() => props.prefix ?? [])
const expanded = ref(new Set<string>())

// Keep the branch of the open folder expanded.
watch(
  () => props.active,
  (active) => {
    const key = active[level.value]
    if (key && active.length > level.value + 1) expanded.value.add(key)
  },
  { immediate: true },
)

function isActive(node: GroupNode): boolean {
  const path = [...base.value, node.key]
  return path.length === props.active.length && path.every((k, i) => k === props.active[i])
}

function toggle(node: GroupNode) {
  const set = new Set(expanded.value)
  if (set.has(node.key)) set.delete(node.key)
  else set.add(node.key)
  expanded.value = set
}
</script>

<template>
  <ul class="flex flex-col" role="group">
    <li v-for="node in nodes" :key="node.key">
      <div
        :class="
          cn(
            'group/node flex h-7 items-center gap-1 rounded-md pr-2 text-sm text-sidebar-foreground/85 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground',
            isActive(node) && 'bg-sidebar-accent font-medium text-sidebar-accent-foreground',
          )
        "
        :style="{ paddingLeft: `${level * 12 + 4}px` }"
      >
        <button
          v-if="node.children.length"
          type="button"
          class="flex size-5 shrink-0 items-center justify-center rounded text-muted-foreground hover:text-foreground"
          :aria-label="label(node.field, node.key, node.label)"
          :aria-expanded="expanded.has(node.key)"
          @click="toggle(node)"
        >
          <ChevronRight
            class="size-3.5 transition-transform"
            :class="expanded.has(node.key) && 'rotate-90'"
          />
        </button>
        <span v-else class="size-5 shrink-0" />
        <button
          type="button"
          class="min-w-0 flex-1 truncate text-left"
          :class="node.key === 'none' && 'text-muted-foreground italic'"
          @click="emit('open', [...base, node.key])"
        >
          {{ label(node.field, node.key, node.label) }}
        </button>
        <span class="tabular font-mono text-[11px] text-muted-foreground">{{ node.count }}</span>
      </div>
      <GroupTree
        v-if="node.children.length && expanded.has(node.key)"
        :nodes="node.children"
        :prefix="[...base, node.key]"
        :active="active"
        :depth="level + 1"
        @open="(p) => emit('open', p)"
      />
    </li>
  </ul>
</template>
