<script setup lang="ts">
import { computed } from 'vue'
import type { RouteLocationRaw } from 'vue-router'
import DetailFields from '@/components/app/DetailFields.vue'
import LevelHeading from '@/components/app/LevelHeading.vue'
import type { Item, Release } from '@/api/types'
import {
  FIELD_KEYS,
  fieldLevel,
  fieldLinks,
  useFieldValue,
  type FieldLevel,
  type ItemFieldKey,
} from '@/lib/itemFields'

/** The fields of one level that have a value: every one on the detail pages (the complete
 * picture), or just `fields` (a view's choice, in the explorer's detail column). With
 * `to`, the heading links to that level's own page. */
const props = defineProps<{
  level: FieldLevel
  title: string
  release: Release
  item?: Item
  scope?: string
  to?: RouteLocationRaw
  fields?: ItemFieldKey[]
  /** Fields the page shows elsewhere already (e.g. in its header). */
  skip?: ItemFieldKey[]
  /** Labels beside values, one field per line (the explorer's narrow column). */
  compact?: boolean
}>()
/** The title is the page's heading already. */
const SKIP = new Set(['game.title'])
/** In the complete picture an object's details stay out, only its main field shows: "Ort"
 * (location.path) without name, type, room, shelf, box; "Plattform" without manufacturer
 * and year. A view's chosen fields show as chosen. */
const PARTS = new Set([
  'platform.manufacturer',
  'platform.year',
  'location.name',
  'location.kind',
  'location.room',
  'location.shelf',
  'location.box',
])
const value = useFieldValue()
const entries = computed(() =>
  (props.fields ?? FIELD_KEYS)
    .filter((k) => fieldLevel(k) === props.level && !SKIP.has(k) && !props.skip?.includes(k))
    .filter((k) => props.fields !== undefined || !PARTS.has(k))
    .map((key) => ({
      key,
      parts: value.parts(key, props.release, props.item),
      links: fieldLinks(key, props.release),
    }))
    .filter((entry) => entry.parts.length),
)
</script>

<template>
  <section
    v-if="entries.length || $slots.default || $slots.before || to"
    class="@container rounded-lg border bg-card p-4"
    :data-testid="`level-card-${level}`"
  >
    <LevelHeading :level="level" :title="title" :scope="scope" :to="to">
      <template v-if="to" #title>
        <RouterLink :to="to" class="hover:underline" :data-testid="`level-link-${level}`">
          {{ title }}
        </RouterLink>
      </template>
    </LevelHeading>
    <slot name="before" />
    <DetailFields v-if="entries.length" :entries="entries" :variant="compact ? 'rows' : 'grid'" />
    <slot />
  </section>
</template>
