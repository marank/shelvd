<script setup lang="ts">
import { Folder } from '@lucide/vue'
import { useI18n } from 'vue-i18n'
import type { GroupNode, Platform } from '@/api/types'
import { brandColor, platformColor, useGroupLabel } from '@/lib/labels'

defineProps<{ nodes: GroupNode[]; platforms: Platform[] }>()
const emit = defineEmits<{ open: [key: string] }>()
const { t, n } = useI18n()
const label = useGroupLabel()

function dot(node: GroupNode, platforms: Platform[]): string | undefined {
  if (node.field === 'platform') {
    const platform = platforms.find((p) => p.id === node.key)
    return platform ? platformColor(platform) : undefined
  }
  if (node.field === 'manufacturer') return brandColor(node.key)
  return undefined
}
</script>

<template>
  <section>
    <h2 class="mb-2 font-mono text-[11px] tracking-wider text-muted-foreground uppercase">
      {{ t('explorer.folders', { n: nodes.length }) }}
    </h2>
    <div
      class="grid grid-cols-1 gap-2 min-[480px]:grid-cols-2 sm:grid-cols-[repeat(auto-fill,minmax(16rem,1fr))]"
    >
      <button
        v-for="node in nodes"
        :key="node.key"
        type="button"
        data-testid="folder"
        class="group/folder flex min-w-0 items-center gap-2.5 rounded-lg border bg-card px-3 py-2.5 sm:px-4 sm:py-3 text-left shadow-xs transition hover:border-primary/40 hover:bg-accent/40 focus-visible:ring-[3px] focus-visible:ring-ring/40 focus-visible:outline-none"
        @click="emit('open', node.key)"
      >
        <span class="relative flex size-9 shrink-0 items-center justify-center rounded-md bg-muted">
          <Folder class="size-4 text-muted-foreground group-hover/folder:text-primary" />
          <span
            v-if="dot(node, platforms)"
            class="absolute -top-0.5 -right-0.5 size-2.5 rounded-full ring-2 ring-card"
            :style="{ backgroundColor: dot(node, platforms) }"
          />
        </span>
        <span class="min-w-0 flex-1">
          <span
            class="block truncate text-sm font-medium"
            :class="node.key === 'none' && 'text-muted-foreground italic'"
          >
            {{ label(node.field, node.key, node.label) }}
          </span>
          <span class="tabular block truncate font-mono text-[11px] text-muted-foreground">
            {{ t('common.items', { n: node.count }, node.count) }}
            <template v-if="Number(node.value) > 0">
              · {{ n(Number(node.value), 'currency') }}
            </template>
            <template v-if="node.children.length">
              · {{ t('explorer.subfolders', { n: node.children.length }, node.children.length) }}
            </template>
          </span>
        </span>
      </button>
    </div>
  </section>
</template>
