<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'

/** Asks before deleting a saved view; loaded only when needed (see SidebarViews). */
defineProps<{ name: string }>()
const emit = defineEmits<{ confirm: []; cancel: [] }>()
const { t } = useI18n()
</script>

<template>
  <Dialog :open="true" @update:open="(v) => !v && emit('cancel')">
    <DialogContent class="sm:max-w-sm">
      <DialogHeader>
        <DialogTitle>{{ t('explorer.deleteView') }}</DialogTitle>
        <DialogDescription>{{ t('explorer.deleteViewHint', { name }) }}</DialogDescription>
      </DialogHeader>
      <DialogFooter>
        <Button variant="ghost" @click="emit('cancel')">{{ t('actions.cancel') }}</Button>
        <Button
          variant="destructive"
          data-testid="sidebar-confirm-delete-view"
          @click="emit('confirm')"
        >
          {{ t('actions.delete') }}
        </Button>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>
