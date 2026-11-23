<script setup lang="ts">
import { ChevronsDownUp, ChevronsUpDown, Rows3 } from '@lucide/vue'
import { useI18n } from 'vue-i18n'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { GROUP_FIELDS, type GroupField } from '@/api/types'
import { useFieldLabel } from '@/lib/itemFields'

/** The field whose groups head sections of the item list ('' = none). With
 * `allCollapsed` set, the menu also folds all sections in or out. */
defineProps<{ modelValue: GroupField | ''; allCollapsed?: boolean | null }>()
const emit = defineEmits<{ 'update:modelValue': [value: GroupField | '']; toggleAll: [] }>()
const { t } = useI18n()
const label = useFieldLabel()

const NONE = '-'
</script>

<template>
  <DropdownMenu>
    <DropdownMenuTrigger as-child>
      <Button
        variant="outline"
        size="sm"
        class="h-8 max-w-56 gap-1 text-xs"
        data-testid="section-picker"
        :aria-label="t('explorer.sections')"
        :title="t('explorer.sections')"
      >
        <Rows3 class="size-4" />
        <span class="truncate">
          {{ modelValue ? label(modelValue) : t('explorer.sections') }}
        </span>
      </Button>
    </DropdownMenuTrigger>
    <DropdownMenuContent align="start" class="max-h-80 w-56 overflow-y-auto">
      <template v-if="allCollapsed !== undefined && allCollapsed !== null">
        <DropdownMenuItem data-testid="toggle-all-sections" @select="emit('toggleAll')">
          <ChevronsUpDown v-if="allCollapsed" class="size-4" />
          <ChevronsDownUp v-else class="size-4" />
          {{ allCollapsed ? t('explorer.expandAll') : t('explorer.collapseAll') }}
        </DropdownMenuItem>
        <DropdownMenuSeparator />
      </template>
      <DropdownMenuRadioGroup
        :model-value="modelValue || NONE"
        @update:model-value="(v) => emit('update:modelValue', v === NONE ? '' : (v as GroupField))"
      >
        <DropdownMenuRadioItem :value="NONE" data-testid="section-none">
          {{ t('explorer.sectionsNone') }}
        </DropdownMenuRadioItem>
        <DropdownMenuSeparator />
        <DropdownMenuRadioItem
          v-for="field in GROUP_FIELDS"
          :key="field"
          :value="field"
          :data-testid="`section-${field}`"
        >
          {{ label(field) }}
        </DropdownMenuRadioItem>
      </DropdownMenuRadioGroup>
    </DropdownMenuContent>
  </DropdownMenu>
</template>
