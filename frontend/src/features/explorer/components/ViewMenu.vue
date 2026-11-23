<script setup lang="ts">
import { Copy, EllipsisVertical, FilePlus2, Pencil, Save, Trash2 } from '@lucide/vue'
import { useI18n } from 'vue-i18n'
import type { RouteLocationRaw } from 'vue-router'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'

/** Everything about the current saved view: save changes, edit, save as new, duplicate,
 * delete. A dot on the button tells there are unsaved changes. */
defineProps<{
  name?: string
  dirty: boolean
  editTo?: RouteLocationRaw
  saveAsNewTo: RouteLocationRaw
  canDelete: boolean
}>()
const emit = defineEmits<{ save: []; duplicate: []; delete: [] }>()
const { t } = useI18n()
</script>

<template>
  <DropdownMenu>
    <DropdownMenuTrigger as-child>
      <Button
        variant="ghost"
        size="icon-sm"
        class="relative"
        :aria-label="
          dirty ? `${t('explorer.viewMenu')} (${t('explorer.unsaved')})` : t('explorer.viewMenu')
        "
        data-testid="view-menu"
      >
        <EllipsisVertical class="size-4" />
        <span
          v-if="dirty"
          class="absolute top-1 right-1 size-2 rounded-full bg-primary"
          data-testid="unsaved-dot"
        />
      </Button>
    </DropdownMenuTrigger>
    <DropdownMenuContent align="end" class="w-64">
      <DropdownMenuLabel v-if="name" class="truncate text-xs text-muted-foreground">
        {{ name }}
      </DropdownMenuLabel>
      <template v-if="dirty">
        <DropdownMenuItem data-testid="save-view" @select="emit('save')">
          <Save class="size-4" /> {{ t('explorer.saveChanges') }}
        </DropdownMenuItem>
        <DropdownMenuSeparator />
      </template>
      <DropdownMenuItem v-if="editTo" as-child>
        <RouterLink :to="editTo" data-testid="edit-view">
          <Pencil class="size-4" /> {{ t('explorer.editView') }}
        </RouterLink>
      </DropdownMenuItem>
      <DropdownMenuItem as-child>
        <RouterLink :to="saveAsNewTo" data-testid="save-as-new">
          <FilePlus2 class="size-4" /> {{ t('explorer.saveAsNew') }}
        </RouterLink>
      </DropdownMenuItem>
      <DropdownMenuItem v-if="editTo" data-testid="duplicate-view" @select="emit('duplicate')">
        <Copy class="size-4" /> {{ t('explorer.duplicateView') }}
      </DropdownMenuItem>
      <template v-if="editTo">
        <DropdownMenuSeparator />
        <DropdownMenuItem
          variant="destructive"
          :disabled="!canDelete"
          data-testid="delete-view"
          @select="emit('delete')"
        >
          <Trash2 class="size-4" />
          <span class="flex flex-col">
            {{ t('explorer.deleteView') }}
            <span v-if="!canDelete" class="text-[11px] text-muted-foreground">
              {{ t('explorer.lastView') }}
            </span>
          </span>
        </DropdownMenuItem>
      </template>
    </DropdownMenuContent>
  </DropdownMenu>
</template>
