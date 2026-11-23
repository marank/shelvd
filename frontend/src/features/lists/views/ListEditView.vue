<script setup lang="ts">
import { Trash2 } from '@lucide/vue'
import { toast } from 'vue-sonner'
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter, type RouteLocationRaw } from 'vue-router'
import EditPage from '@/components/app/EditPage.vue'
import EditSection from '@/components/app/EditSection.vue'
import { ApiError } from '@/api/errors'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Spinner } from '@/components/ui/spinner'
import { Textarea } from '@/components/ui/textarea'
import ConfirmDialog from '@/components/app/ConfirmDialog.vue'
import PublicLinkCard from '../components/PublicLinkCard.vue'
import {
  useAddEntry,
  useCreateList,
  useDeleteList,
  useList,
  useUpdateList,
} from '../composables/useLists'

/**
 * Create (route list-new) or edit (list-edit) a list. list-new accepts ?release=&item= to add
 * that game right after creating, and ?back=<path> to return to the referring page.
 */
const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const listId = computed(() => (route.params.listId as string | undefined) ?? '')
const isNew = computed(() => !listId.value)
const query = (name: string) => {
  const value = route.query[name]
  return typeof value === 'string' && value ? value : undefined
}
/** Only same-app paths are accepted as "back" targets. */
const backPath = computed(() => {
  const value = query('back')
  return value?.startsWith('/') && !value.startsWith('//') ? value : undefined
})

const list = useList(listId)
const create = useCreateList()
const update = useUpdateList(listId)
const remove = useDeleteList(listId)
const addEntry = useAddEntry()

const back = computed<RouteLocationRaw>(() => {
  if (backPath.value) return backPath.value
  return isNew.value ? { name: 'lists' } : { name: 'list-detail', params: { listId: listId.value } }
})
const loadError = computed(() => {
  if (isNew.value || !list.isError.value) return ''
  const error = list.error.value
  return error instanceof ApiError && error.status === 404
    ? t('lists.notFound')
    : (error?.message ?? t('errors.generic'))
})

const form = ref({ name: '', description: '' })
const loaded = ref(false)
watch(listId, () => (loaded.value = false))
watch(
  [() => list.data.value, loaded],
  () => {
    if (loaded.value || isNew.value || !list.data.value) return
    form.value = { name: list.data.value.name, description: list.data.value.description }
    loaded.value = true
  },
  { immediate: true },
)

const busy = computed(
  () => create.isPending.value || update.isPending.value || addEntry.isPending.value,
)
const error = ref('')

async function save() {
  const body = { name: form.value.name.trim(), description: form.value.description.trim() }
  if (!body.name) {
    error.value = t('lists.nameRequired')
    return
  }
  error.value = ''
  try {
    if (!isNew.value) {
      await update.mutateAsync(body)
      toast.success(t('lists.saved'))
      await router.push(back.value)
      return
    }
    const created = await create.mutateAsync(body)
    await addAfterCreate(created)
  } catch (e) {
    error.value = e instanceof Error ? e.message : t('errors.generic')
  }
}

/** The list exists now: add the game it was created for (if any) and leave the page. */
async function addAfterCreate(created: { id: string; name: string }) {
  const detail = { name: 'list-detail', params: { listId: created.id } }
  const releaseId = query('release')
  if (!releaseId) {
    toast.success(t('lists.created'))
    await router.push(backPath.value ?? detail)
    return
  }
  try {
    await addEntry.mutateAsync({ listId: created.id, releaseId, itemId: query('item') })
    toast.success(t('lists.added', { name: created.name }))
    await router.push(backPath.value ?? detail)
  } catch (e) {
    // Don't stay on the form: submitting again would create a second list.
    toast.error(e instanceof Error ? e.message : t('errors.generic'))
    await router.push(detail)
  }
}

const deleting = ref(false)
async function destroy() {
  try {
    await remove.mutateAsync()
    deleting.value = false
    toast.success(t('lists.deleted'))
    await router.push({ name: 'lists' })
  } catch (e) {
    toast.error(e instanceof Error ? e.message : t('errors.generic'))
  }
}
</script>

<template>
  <div class="flex min-h-0 min-w-0 flex-1 flex-col" data-testid="ListEditView">
    <div v-if="!isNew && list.isPending.value" class="flex justify-center py-10">
      <Spinner class="size-6" />
    </div>
    <div v-else-if="loadError" class="p-4 md:px-6">
      <Alert variant="destructive">
        <AlertDescription data-testid="list-load-error">{{ loadError }}</AlertDescription>
      </Alert>
      <Button as-child variant="outline" class="mt-4">
        <RouterLink :to="{ name: 'lists' }">{{ t('lists.backToLists') }}</RouterLink>
      </Button>
    </div>
    <EditPage
      v-else
      :title="isNew ? t('lists.newList') : t('lists.editList')"
      :description="isNew ? t('lists.subtitle') : list.data.value?.name"
      :back="back"
      :busy="busy"
      :save-label="isNew ? t('actions.create') : t('actions.save')"
      :error="error"
      @submit="save"
    >
      <EditSection :title="t('lists.general')" :description="t('lists.generalHint')">
        <div class="grid gap-1.5 sm:col-span-2">
          <Label for="list-name">{{ t('fields.name') }}</Label>
          <Input
            id="list-name"
            v-model="form.name"
            required
            maxlength="200"
            :placeholder="t('lists.namePlaceholder')"
          />
        </div>
        <div class="grid gap-1.5 sm:col-span-2">
          <Label for="list-description">
            {{ t('fields.description') }}
            <span class="text-muted-foreground">({{ t('common.optional') }})</span>
          </Label>
          <Textarea
            id="list-description"
            v-model="form.description"
            rows="3"
            :placeholder="t('lists.descriptionPlaceholder')"
          />
        </div>
      </EditSection>

      <EditSection
        v-if="list.data.value && !isNew"
        :title="t('lists.publicLink')"
        :description="t('lists.publicLinkHint')"
      >
        <PublicLinkCard
          class="sm:col-span-2"
          :list-id="listId"
          :token="list.data.value.public_token"
        />
      </EditSection>

      <template v-if="list.data.value && !isNew" #actions>
        <Button
          type="button"
          variant="ghost"
          class="text-destructive"
          data-testid="delete-list"
          @click="deleting = true"
        >
          <Trash2 />
          <span class="hidden sm:inline">{{ t('actions.delete') }}</span>
        </Button>
      </template>
    </EditPage>

    <ConfirmDialog
      v-model:open="deleting"
      :title="t('lists.deleteList')"
      :description="t('lists.deleteConfirm', { name: list.data.value?.name ?? '' })"
      :busy="remove.isPending.value"
      @confirm="destroy"
    />
  </div>
</template>
