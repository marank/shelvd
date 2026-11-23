<script setup lang="ts">
import NativeSelect from '@/components/app/NativeSelect.vue'
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { toast } from 'vue-sonner'
import type { Library } from '@/api/types'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Spinner } from '@/components/ui/spinner'
import { Textarea } from '@/components/ui/textarea'
import { errorMessage } from '../../composables/format'
import { useLibraryMutations } from '../../composables/useLibrarySettings'

const props = defineProps<{ library: Library; isOwner: boolean }>()
const { t } = useI18n()
const { update } = useLibraryMutations(() => props.library.id)

const name = ref('')
const description = ref('')
const viewerLoans = ref<Library['viewer_loans']>('status')
watch(
  () => props.library,
  (library) => {
    name.value = library.name
    description.value = library.description
    viewerLoans.value = library.viewer_loans
  },
  { immediate: true },
)

async function save() {
  if (!name.value.trim()) return
  try {
    await update.mutateAsync({
      name: name.value.trim(),
      description: description.value,
      viewer_loans: viewerLoans.value,
    })
    toast.success(t('manage.settings.saved'))
  } catch (e) {
    toast.error(errorMessage(e, t('errors.generic')))
  }
}
</script>

<template>
  <Card data-testid="settings-general">
    <CardHeader>
      <CardTitle>{{ t('manage.settings.general') }}</CardTitle>
      <CardDescription>
        {{ isOwner ? t('manage.settings.generalHint') : t('manage.settings.ownerOnly') }}
      </CardDescription>
    </CardHeader>
    <CardContent>
      <form class="grid gap-4" @submit.prevent="save">
        <div class="grid gap-2">
          <Label for="library-name">{{ t('fields.name') }}</Label>
          <Input id="library-name" v-model="name" :disabled="!isOwner" required />
        </div>
        <div class="grid gap-2">
          <Label for="library-description">{{ t('fields.description') }}</Label>
          <Textarea id="library-description" v-model="description" :disabled="!isOwner" rows="3" />
        </div>
        <div class="grid gap-2">
          <Label for="library-viewer-loans">{{ t('manage.settings.viewerLoans') }}</Label>
          <NativeSelect
            id="library-viewer-loans"
            v-model="viewerLoans"
            :disabled="!isOwner"
            data-testid="viewer-loans"
          >
            <option value="status">{{ t('manage.settings.viewerLoansStatus') }}</option>
            <option value="hidden">{{ t('manage.settings.viewerLoansHidden') }}</option>
          </NativeSelect>
          <p class="text-xs text-muted-foreground">{{ t('manage.settings.viewerLoansHint') }}</p>
        </div>
        <div v-if="isOwner">
          <Button type="submit" data-testid="general-save" :disabled="update.isPending.value">
            <Spinner v-if="update.isPending.value" />
            {{ t('actions.save') }}
          </Button>
        </div>
      </form>
    </CardContent>
  </Card>
</template>
