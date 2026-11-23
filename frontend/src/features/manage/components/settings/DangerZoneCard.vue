<script setup lang="ts">
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { toast } from 'vue-sonner'
import type { Library } from '@/api/types'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { errorMessage } from '../../composables/format'
import { useLibraryMutations } from '../../composables/useLibrarySettings'
import ConfirmDialog from '@/components/app/ConfirmDialog.vue'

const props = defineProps<{ library: Library }>()
const { t } = useI18n()
const router = useRouter()
const { remove } = useLibraryMutations(() => props.library.id)

const open = ref(false)
const typed = ref('')
const error = ref('')
const matches = computed(() => typed.value.trim() === props.library.name)

function start() {
  typed.value = ''
  error.value = ''
  open.value = true
}
async function confirm() {
  if (!matches.value) return
  try {
    await remove.mutateAsync()
    open.value = false
    toast.success(t('manage.settings.deleted', { name: props.library.name }))
    await router.push({ name: 'home' })
  } catch (e) {
    error.value = errorMessage(e, t('errors.generic'))
  }
}
</script>

<template>
  <Card class="ring-destructive/30" data-testid="settings-danger">
    <CardHeader>
      <CardTitle class="text-destructive">{{ t('manage.settings.danger') }}</CardTitle>
      <CardDescription>{{ t('manage.settings.deleteHint') }}</CardDescription>
    </CardHeader>
    <CardContent>
      <Button variant="destructive" data-testid="library-delete" @click="start">
        {{ t('manage.settings.deleteLibrary') }}
      </Button>
    </CardContent>
    <ConfirmDialog
      v-model:open="open"
      :title="t('manage.settings.deleteTitle', { name: library.name })"
      :description="t('manage.settings.deleteConfirmHint')"
      :confirm-label="t('manage.settings.deleteLibrary')"
      :busy="remove.isPending.value"
      :disabled="!matches"
      :error="error"
      @confirm="confirm"
    >
      <div class="grid gap-2">
        <Label for="confirm-name">
          {{ t('manage.settings.typeName', { name: library.name }) }}
        </Label>
        <Input id="confirm-name" v-model="typed" autocomplete="off" data-testid="confirm-name" />
      </div>
    </ConfirmDialog>
  </Card>
</template>
