<script setup lang="ts">
import { ListPlus, Plus } from '@lucide/vue'
import { toast } from 'vue-sonner'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import { ApiError } from '@/api/errors'
import type { CustomList } from '@/api/types'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuSub,
  DropdownMenuSubContent,
  DropdownMenuSubTrigger,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { useAddEntry, useLists } from '../composables/useLists'

/** "Add to list" dropdown for a release (and optionally the concrete item).
 * `sub`: render as a submenu inside another dropdown (e.g. a copy's ⋮ menu). */
const props = defineProps<{ releaseId: string; itemId?: string; sub?: boolean }>()

const { t } = useI18n()
const lists = useLists()
const add = useAddEntry()
const route = useRoute()
const router = useRouter()

async function addTo(list: Pick<CustomList, 'id' | 'name'>) {
  try {
    await add.mutateAsync({ listId: list.id, releaseId: props.releaseId, itemId: props.itemId })
    toast.success(t('lists.added', { name: list.name }))
  } catch (error) {
    if (error instanceof ApiError && error.status === 409) {
      toast.info(t('lists.alreadyOnList', { name: list.name }))
    } else {
      toast.error(error instanceof Error ? error.message : t('errors.generic'))
    }
  }
}

/** Create a list on its own page; it adds this game and comes back here afterwards. */
function newList() {
  void router.push({
    name: 'list-new',
    query: {
      release: props.releaseId,
      ...(props.itemId ? { item: props.itemId } : {}),
      back: route.fullPath,
    },
  })
}
</script>

<template>
  <component :is="sub ? DropdownMenuSub : DropdownMenu">
    <DropdownMenuSubTrigger v-if="sub" data-testid="add-to-list">
      <ListPlus class="size-4" />
      {{ t('lists.addToList') }}
    </DropdownMenuSubTrigger>
    <DropdownMenuTrigger v-else as-child>
      <slot>
        <Button variant="outline" size="sm" data-testid="add-to-list">
          <ListPlus />
          {{ t('lists.addToList') }}
        </Button>
      </slot>
    </DropdownMenuTrigger>
    <component
      :is="sub ? DropdownMenuSubContent : DropdownMenuContent"
      v-bind="sub ? {} : { align: 'end' }"
      class="w-56"
    >
      <DropdownMenuLabel>{{ t('lists.title') }}</DropdownMenuLabel>
      <DropdownMenuItem
        v-for="list in lists.data.value ?? []"
        :key="list.id"
        data-testid="add-to-list-item"
        :disabled="add.isPending.value"
        @select="addTo(list)"
      >
        <span class="min-w-0 flex-1 truncate">{{ list.name }}</span>
        <span class="font-mono text-xs text-muted-foreground tabular">
          {{ list.entry_count }}
        </span>
      </DropdownMenuItem>
      <DropdownMenuItem v-if="lists.data.value?.length === 0" disabled>
        {{ t('lists.noLists') }}
      </DropdownMenuItem>
      <DropdownMenuSeparator />
      <DropdownMenuItem data-testid="add-to-new-list" @select="newList">
        <Plus />
        {{ t('lists.newListEllipsis') }}
      </DropdownMenuItem>
    </component>
  </component>
</template>
