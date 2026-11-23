<script setup lang="ts">
import { ArrowRight, Trash2 } from '@lucide/vue'
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { toast } from 'vue-sonner'
import { useRoute, useRouter } from 'vue-router'
import EditPage from '@/components/app/EditPage.vue'
import EditSection from '@/components/app/EditSection.vue'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Spinner } from '@/components/ui/spinner'
import { Textarea } from '@/components/ui/textarea'
import { canEdit, useLibrary } from '@/features/library/composables/useLibraries'
import { usePeople } from '@/features/library/composables/useReference'
import ConfirmDialog from '@/components/app/ConfirmDialog.vue'
import { errorMessage, formatDate } from '../composables/format'
import { useLoans } from '../composables/useLoans'
import { usePersonMutations } from '../composables/usePersonMutations'

/** Create (route person-new) or edit (person-edit) one person of a library. */
const { t, locale } = useI18n()
const route = useRoute()
const router = useRouter()
const libraryId = computed(() => String(route.params.libraryId ?? ''))
const personId = computed(() => (route.params.personId as string | undefined) ?? '')
const isNew = computed(() => !personId.value)
const library = useLibrary(libraryId)
const editable = computed(() => canEdit(library.data.value?.role))

const people = usePeople(libraryId)
const person = computed(() => people.data.value?.find((p) => p.id === personId.value))
const notFound = computed(() => !isNew.value && people.isSuccess.value && !person.value)

const back = computed(() => ({ name: 'people', params: { libraryId: libraryId.value } }))

const form = ref({ name: '', email: '', notes: '' })
const loaded = ref(false)
watch(personId, () => (loaded.value = false))
watch(
  [person, loaded],
  () => {
    if (loaded.value || isNew.value) return
    if (!person.value) return
    form.value = { name: person.value.name, email: person.value.email, notes: person.value.notes }
    loaded.value = true
  },
  { immediate: true },
)

const openLoans = useLoans(libraryId, true)
const loans = computed(() =>
  (openLoans.data.value ?? []).filter((l) => l.borrower.id === personId.value),
)
const date = (value: string | null | undefined) => formatDate(value, locale.value)
const explorerLink = (query: Record<string, string>) => ({
  name: 'explorer',
  params: { libraryId: libraryId.value },
  query,
})

const { create, update, remove } = usePersonMutations(libraryId)
const busy = computed(() => create.isPending.value || update.isPending.value)
const error = ref('')

async function save() {
  if (!editable.value) {
    error.value = t('manage.readOnly')
    return
  }
  const body = { ...form.value, name: form.value.name.trim(), email: form.value.email.trim() }
  if (!body.name) {
    error.value = t('manage.people.nameRequired')
    return
  }
  error.value = ''
  try {
    if (isNew.value) await create.mutateAsync(body)
    else await update.mutateAsync({ id: personId.value, body })
    toast.success(t('manage.people.saved', { name: body.name }))
    await router.push(back.value)
  } catch (e) {
    error.value = errorMessage(e, t('errors.generic'))
  }
}

const deleteOpen = ref(false)
const deleteError = ref('')
function startDelete() {
  deleteError.value = ''
  deleteOpen.value = true
}
async function confirmDelete() {
  const name = person.value?.name ?? ''
  try {
    await remove.mutateAsync(personId.value)
    toast.success(t('manage.people.deleted', { name }))
    deleteOpen.value = false
    await router.push(back.value)
  } catch (e) {
    // 409: the person still has open loans – the backend says so.
    deleteError.value = errorMessage(e, t('errors.generic'))
  }
}
</script>

<template>
  <div class="flex min-h-0 min-w-0 flex-1 flex-col" data-testid="PersonEditView">
    <div v-if="!isNew && people.isPending.value" class="flex justify-center py-10">
      <Spinner class="size-6" />
    </div>
    <div v-else-if="!isNew && (people.isError.value || notFound)" class="p-4 md:px-6">
      <Alert variant="destructive">
        <AlertDescription data-testid="person-load-error">
          {{
            notFound
              ? t('manage.people.notFound')
              : errorMessage(people.error.value, t('errors.generic'))
          }}
        </AlertDescription>
      </Alert>
      <Button as-child variant="outline" class="mt-4">
        <RouterLink :to="back">{{ t('manage.people.title') }}</RouterLink>
      </Button>
    </div>
    <EditPage
      v-else
      :title="isNew ? t('manage.people.add') : t('manage.people.editTitle')"
      :description="isNew ? t('manage.people.dialogHint') : person?.name"
      :back="back"
      :busy="busy"
      :save-label="isNew ? t('actions.create') : t('actions.save')"
      :error="error"
      @submit="save"
    >
      <EditSection :title="t('manage.people.contact')" :description="t('manage.people.dialogHint')">
        <div class="grid gap-1.5">
          <Label for="person-name">{{ t('fields.name') }}</Label>
          <Input id="person-name" v-model="form.name" required autocomplete="off" />
        </div>
        <div class="grid gap-1.5">
          <Label for="person-email">
            {{ t('fields.email') }}
            <span class="text-muted-foreground">({{ t('common.optional') }})</span>
          </Label>
          <Input id="person-email" v-model="form.email" type="email" autocomplete="off" />
        </div>
        <div class="grid gap-1.5 sm:col-span-2">
          <Label for="person-notes">
            {{ t('fields.notes') }}
            <span class="text-muted-foreground">({{ t('common.optional') }})</span>
          </Label>
          <Textarea id="person-notes" v-model="form.notes" rows="3" />
        </div>
      </EditSection>

      <EditSection
        v-if="person"
        :title="t('manage.people.lentItems')"
        :description="t('manage.people.loansHint')"
      >
        <div class="grid gap-3 sm:col-span-2">
          <div v-if="openLoans.isPending.value" class="flex py-2"><Spinner /></div>
          <p
            v-else-if="!loans.length"
            class="text-sm text-muted-foreground"
            data-testid="person-no-loans"
          >
            {{ t('manage.people.noOpenLoans') }}
          </p>
          <ul v-else class="divide-y rounded-lg border bg-card text-sm">
            <li
              v-for="loan in loans"
              :key="loan.id"
              class="flex flex-wrap items-center gap-x-3 gap-y-1 px-3 py-2"
              data-testid="person-loan"
            >
              <RouterLink
                :to="explorerLink({ item: loan.item_id })"
                class="min-w-0 flex-1 truncate font-medium hover:underline"
              >
                {{ loan.item_title }}
              </RouterLink>
              <Badge v-if="loan.overdue" variant="destructive">
                {{ t('manage.loans.overdue') }}
              </Badge>
              <span class="font-mono text-xs text-muted-foreground tabular-nums">
                {{ date(loan.lent_on) }}
                <template v-if="loan.due_on"> → {{ date(loan.due_on) }}</template>
              </span>
            </li>
          </ul>
          <div class="flex flex-wrap gap-2">
            <Button as-child variant="outline" size="sm">
              <RouterLink
                :to="explorerLink({ g: 'owner', p: personId })"
                data-testid="person-owned"
              >
                {{ t('manage.people.ownedItems') }}
                <ArrowRight />
              </RouterLink>
            </Button>
            <Button as-child variant="ghost" size="sm">
              <RouterLink :to="{ name: 'loans', params: { libraryId } }">
                {{ t('manage.loans.title') }}
                <ArrowRight />
              </RouterLink>
            </Button>
          </div>
        </div>
      </EditSection>

      <template v-if="person && editable" #actions>
        <Button
          type="button"
          variant="ghost"
          class="text-destructive"
          data-testid="person-delete"
          @click="startDelete"
        >
          <Trash2 />
          <span class="hidden sm:inline">{{ t('actions.delete') }}</span>
        </Button>
      </template>
    </EditPage>

    <ConfirmDialog
      v-model:open="deleteOpen"
      :title="t('manage.people.deleteTitle', { name: person?.name ?? '' })"
      :description="t('manage.people.deleteHint')"
      :busy="remove.isPending.value"
      :error="deleteError"
      @confirm="confirmDelete"
    />
  </div>
</template>
