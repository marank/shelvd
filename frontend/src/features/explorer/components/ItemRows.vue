<script setup lang="ts">
import { ArrowDown, ArrowUp, ChevronsUpDown, HandCoins } from '@lucide/vue'
import { useI18n } from 'vue-i18n'
import CoverImage from '@/components/app/CoverImage.vue'
import PlatformBadge from '@/components/app/PlatformBadge.vue'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import type { Item } from '@/api/types'
import {
  isMono,
  isNumeric,
  useFieldLabel,
  useFieldValue,
  type ItemFieldKey,
} from '@/lib/itemFields'
import { cn } from '@/lib/utils'

/** List and table layouts; which fields they show comes from the view (`fields`). */
const props = defineProps<{
  items: Item[]
  fields: ItemFieldKey[]
  layout: 'list' | 'table'
  selectedId?: string
  /** Column the table is sorted by (header click), if any. */
  sortKey?: ItemFieldKey | null
  sortDesc?: boolean
}>()
const emit = defineEmits<{ open: [id: string]; sortBy: [key: ItemFieldKey] }>()
const ariaSort = (key: ItemFieldKey) =>
  props.sortKey === key ? (props.sortDesc ? 'descending' : 'ascending') : undefined
const { t } = useI18n()
const value = useFieldValue()
const label = useFieldLabel()
const meta = (item: Item) =>
  props.fields
    .filter((key) => key !== 'platform.name')
    .map((key) => value(key, item))
    .filter(Boolean)
    .join(' · ')
</script>

<template>
  <ul v-if="layout === 'list'" class="divide-y rounded-lg border bg-card">
    <li v-for="item in items" :key="item.id">
      <button
        type="button"
        data-testid="item-row"
        :data-item-id="item.id"
        :class="item.id === selectedId && 'bg-accent'"
        class="flex w-full min-w-0 items-center gap-3 px-3 py-2 text-left hover:bg-accent/50 focus-visible:bg-accent/50 focus-visible:outline-none"
        @click="emit('open', item.id)"
      >
        <CoverImage
          fit="box"
          :src="item.cover_url"
          :title="item.title"
          :manufacturer="item.release.platform.manufacturer"
          class="w-9 shrink-0 rounded-sm"
        />
        <span class="min-w-0 flex-1">
          <span class="block truncate text-sm font-medium">{{ item.title }}</span>
          <span class="block truncate font-mono text-[11px] text-muted-foreground">
            {{ meta(item) || '—' }}
          </span>
        </span>
        <HandCoins
          v-if="item.active_loan"
          class="size-4 shrink-0 text-warning"
          :aria-label="
            item.active_loan.borrower
              ? t('explorer.lentTo', { name: item.active_loan.borrower.name })
              : t('items.lent')
          "
        />
        <PlatformBadge :platform="item.release.platform" class="shrink-0" />
      </button>
    </li>
  </ul>
  <div v-else class="overflow-x-auto rounded-lg border bg-card">
    <Table class="text-[13px]">
      <TableHeader>
        <TableRow class="font-mono text-[11px] tracking-wider uppercase">
          <TableHead
            v-for="key in ['game.title' as const, ...fields]"
            :key="key"
            :aria-sort="ariaSort(key)"
            :class="isNumeric(key) && 'text-right'"
            :data-testid="`column-${key}`"
          >
            <button
              type="button"
              class="group/sort inline-flex items-center gap-1 uppercase hover:text-foreground"
              :class="sortKey === key && 'text-foreground'"
              :data-testid="`sort-by-${key}`"
              @click="emit('sortBy', key)"
            >
              {{ label(key) }}
              <ArrowUp v-if="sortKey === key && !sortDesc" class="size-3" />
              <ArrowDown v-else-if="sortKey === key" class="size-3" />
              <ChevronsUpDown
                v-else
                class="size-3 opacity-0 transition-opacity group-hover/sort:opacity-60"
              />
            </button>
          </TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        <TableRow
          v-for="item in items"
          :key="item.id"
          data-testid="item-table-row"
          :data-item-id="item.id"
          :data-state="item.id === selectedId ? 'selected' : undefined"
          class="cursor-pointer"
          tabindex="0"
          @click="emit('open', item.id)"
          @keydown.enter="emit('open', item.id)"
        >
          <TableCell class="max-w-72 font-medium">
            <span class="flex items-center gap-1.5">
              <span class="truncate">{{ item.title }}</span>
              <HandCoins
                v-if="item.active_loan"
                class="size-3.5 shrink-0 text-warning"
                :aria-label="
                  item.active_loan.borrower
                    ? t('explorer.lentTo', { name: item.active_loan.borrower.name })
                    : t('items.lent')
                "
              />
            </span>
          </TableCell>
          <TableCell
            v-for="key in fields"
            :key="key"
            :class="
              cn(
                'max-w-56 truncate',
                isMono(key) && 'tabular font-mono text-xs',
                isNumeric(key) && 'text-right',
              )
            "
          >
            <PlatformBadge v-if="key === 'platform.name'" :platform="item.release.platform" />
            <template v-else>
              {{ value(key, item) || '—' }}
            </template>
          </TableCell>
        </TableRow>
      </TableBody>
    </Table>
  </div>
</template>
