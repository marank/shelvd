<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { toast } from 'vue-sonner'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import type { Item } from '@/api/types'
import { useItemMutations } from '@/features/items/composables/useItem'

/** "Delete this copy?" – open while `item` is set. */
const props = defineProps<{ libraryId: string }>()
const item = defineModel<Item | null>('item', { required: true })
const emit = defineEmits<{ deleted: [item: Item] }>()
const { t } = useI18n()
const { remove } = useItemMutations(() => props.libraryId)

async function confirm() {
  const doomed = item.value
  if (!doomed) return
  await remove.mutateAsync(doomed.id)
  item.value = null
  toast.success(t('items.deleted'))
  emit('deleted', doomed)
}
</script>

<template>
  <Dialog :open="!!item" @update:open="(open) => !open && (item = null)">
    <DialogContent class="sm:max-w-sm">
      <DialogHeader>
        <DialogTitle>{{ t('items.deleteCopy') }}</DialogTitle>
        <DialogDescription>
          {{ t('items.deleteHint', { title: item?.title ?? '' }) }}
        </DialogDescription>
      </DialogHeader>
      <DialogFooter>
        <Button variant="ghost" @click="item = null">{{ t('actions.cancel') }}</Button>
        <Button
          variant="destructive"
          data-testid="confirm-delete"
          :disabled="remove.isPending.value"
          @click="confirm"
        >
          {{ t('actions.delete') }}
        </Button>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>
