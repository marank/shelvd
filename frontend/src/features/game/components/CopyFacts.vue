<script setup lang="ts">
// The copy you look at, as the page's one card (it's yours; the catalog details aren't
// boxed): its facts in three groups side by side – where it is, its state (format
// included), what it cost – each a list of icon and value (the field's name as a
// tooltip); its notes as a footer. Its actions sit in the section's heading; platform and
// region are the release's, whether it's lent is a figure in the page's head.
import {
  BadgeCheck,
  CalendarDays,
  Disc3,
  Gamepad2,
  MapPin,
  Package,
  Receipt,
  Sparkles,
  Tags,
  TrendingUp,
  User,
  type LucideIcon,
} from '@lucide/vue'
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import type { Item } from '@/api/types'
import { useFieldLabel, useFieldValue, type ItemFieldKey } from '@/lib/itemFields'

const props = defineProps<{ item: Item }>()
const { t, n } = useI18n()
const label = useFieldLabel()
const value = useFieldValue()

const ICONS: Partial<Record<ItemFieldKey, LucideIcon>> = {
  'location.path': MapPin,
  'owner.name': User,
  'copy.status': BadgeCheck,
  'copy.format': Disc3,
  'copy.completeness': Package,
  'copy.condition': Sparkles,
  'copy.progress': Gamepad2,
  'copy.tags': Tags,
  'copy.acquired': CalendarDays,
  'copy.price': Receipt,
  'copy.value': TrendingUp,
}

/** The value against what was paid, e.g. "+12 %". */
const change = computed(() => {
  const now = Number(props.item.current_value) || 0
  const paid = Number(props.item.purchase_price) || 0
  if (!now || !paid) return ''
  const percent = Math.round(((now - paid) / paid) * 100)
  return `${percent > 0 ? '+' : ''}${n(percent)} %`
})

const groups = computed(() =>
  (
    [
      { key: 'place', fields: ['location.path', 'owner.name'] },
      {
        key: 'state',
        fields: [
          ...(props.item.status !== 'owned' ? (['copy.status'] as ItemFieldKey[]) : []),
          'copy.format',
          'copy.completeness',
          'copy.condition',
          'copy.progress',
          'copy.tags',
        ],
      },
      { key: 'purchase', fields: ['copy.acquired', 'copy.price', 'copy.value'] },
    ] as { key: string; fields: ItemFieldKey[] }[]
  )
    .map((group) => ({
      key: group.key,
      entries: group.fields
        .map((field) => ({
          field,
          icon: ICONS[field]!,
          text: [
            value.parts(field, props.item.release, props.item).join(', '),
            field === 'copy.value' ? change.value : '',
          ]
            .filter(Boolean)
            .join(' · '),
        }))
        .filter((entry) => entry.text && !entry.text.startsWith(' · ')),
    }))
    .filter((group) => group.entries.length),
)
</script>

<template>
  <div class="overflow-hidden rounded-lg border bg-card" data-testid="copy-facts">
    <!-- As many equal columns as there are groups (viewers see no purchase). -->
    <div
      v-if="groups.length"
      class="grid grid-cols-1 divide-y @lg:divide-x @lg:divide-y-0"
      :class="groups.length === 3 ? '@lg:grid-cols-3' : groups.length === 2 && '@lg:grid-cols-2'"
      data-testid="copy-groups"
    >
      <div
        v-for="group in groups"
        :key="group.key"
        class="px-4 py-3"
        :data-testid="`copy-group-${group.key}`"
      >
        <p class="mb-2 font-mono text-[11px] tracking-wider text-muted-foreground uppercase">
          {{ t(`items.page.groups.${group.key}`) }}
        </p>
        <ul class="space-y-1.5 text-sm">
          <li
            v-for="entry in group.entries"
            :key="entry.field"
            class="flex items-start gap-2"
            :title="label(entry.field)"
            :data-field="entry.field"
          >
            <component :is="entry.icon" class="mt-0.5 size-4 shrink-0 text-muted-foreground" />
            <span class="sr-only">{{ label(entry.field) }}:</span>
            <span class="min-w-0 break-words">{{ entry.text }}</span>
          </li>
        </ul>
      </div>
    </div>

    <p
      v-if="item.notes"
      class="border-t px-4 py-3 text-sm whitespace-pre-line text-muted-foreground"
      data-testid="copy-notes"
    >
      {{ item.notes }}
    </p>
  </div>
</template>
