<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Spinner } from '@/components/ui/spinner'

/** Confirmation for destructive actions. */
defineProps<{
  title: string
  description?: string
  confirmLabel?: string
  busy?: boolean
  error?: string
  disabled?: boolean
}>()
const open = defineModel<boolean>('open', { default: false })
const emit = defineEmits<{ confirm: [] }>()
const { t } = useI18n()
</script>

<template>
  <Dialog v-model:open="open">
    <DialogContent data-testid="confirm-dialog">
      <DialogHeader>
        <DialogTitle>{{ title }}</DialogTitle>
        <DialogDescription v-if="description">{{ description }}</DialogDescription>
      </DialogHeader>
      <slot />
      <Alert v-if="error" variant="destructive">
        <AlertDescription data-testid="confirm-error">{{ error }}</AlertDescription>
      </Alert>
      <DialogFooter>
        <Button variant="outline" @click="open = false">{{ t('actions.cancel') }}</Button>
        <Button
          variant="destructive"
          data-testid="confirm-button"
          :disabled="busy || disabled"
          @click="emit('confirm')"
        >
          <Spinner v-if="busy" />
          {{ confirmLabel ?? t('actions.delete') }}
        </Button>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>
