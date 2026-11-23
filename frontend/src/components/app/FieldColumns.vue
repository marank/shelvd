<script setup lang="ts">
// Fields in as many columns as there are groups (up to four), read top to bottom: each column is a group of fields that
// belong together (platform, region, edition, date …). Empty groups drop out.
import { computed } from 'vue'
import type { Item, Release } from '@/api/types'
import { fieldLinks, useFieldValue, type ItemFieldKey } from '@/lib/itemFields'
import DetailFields from './DetailFields.vue'

const props = defineProps<{
  groups: ItemFieldKey[][]
  release: Release
  item?: Item
  /** Own texts for some fields ("12.12.1998 (N64)"); an empty one hides the field. */
  texts?: Partial<Record<ItemFieldKey, string>>
}>()
const value = useFieldValue()
/** Static class names (Tailwind only sees whole ones). */
const WIDE: Record<number, string> = {
  2: '@2xl:grid-cols-2',
  3: '@2xl:grid-cols-3',
  4: '@2xl:grid-cols-4',
}
const columns = computed(() =>
  props.groups
    .map((keys) =>
      keys
        .map((key) => ({
          key,
          parts:
            props.texts && key in props.texts
              ? [props.texts[key]].filter((text): text is string => !!text)
              : value.parts(key, props.release, props.item),
          links: fieldLinks(key, props.release),
        }))
        .filter((entry) => entry.parts.length),
    )
    .filter((column) => column.length),
)
</script>

<template>
  <div
    v-if="columns.length"
    class="grid grid-cols-2 gap-x-6 gap-y-5"
    :class="WIDE[columns.length]"
    data-testid="field-columns"
  >
    <DetailFields v-for="(column, i) in columns" :key="i" :entries="column" variant="stack" />
  </div>
</template>
