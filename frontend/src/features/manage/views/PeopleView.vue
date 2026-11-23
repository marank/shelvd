<script setup lang="ts">
import { Pencil, Plus, Trash2, Users } from '@lucide/vue'
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { toast } from 'vue-sonner'
import { useRoute } from 'vue-router'
import type { Person } from '@/api/types'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Empty,
  EmptyContent,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from '@/components/ui/empty'
import { Spinner } from '@/components/ui/spinner'
import { canEdit, useLibrary } from '@/features/library/composables/useLibraries'
import { usePeople } from '@/features/library/composables/useReference'
import ConfirmDialog from '@/components/app/ConfirmDialog.vue'
import { errorMessage } from '../composables/format'
import { usePersonMutations } from '../composables/usePersonMutations'

const { t } = useI18n()
const route = useRoute()
const libraryId = computed(() => String(route.params.libraryId ?? ''))
const library = useLibrary(libraryId)
const editable = computed(() => canEdit(library.data.value?.role))

const people = usePeople(libraryId)
const rows = computed(() =>
  [...(people.data.value ?? [])].sort((a, b) => a.name.localeCompare(b.name)),
)

const explorerLink = (field: 'owner' | 'borrower', person: Person) => ({
  name: 'explorer',
  params: { libraryId: libraryId.value },
  query: { g: field, p: person.id },
})

const { remove } = usePersonMutations(libraryId)

const newLink = computed(() => ({ name: 'person-new', params: { libraryId: libraryId.value } }))
const editLink = (person: Person) => ({
  name: 'person-edit',
  params: { libraryId: libraryId.value, personId: person.id },
})

// Delete
const deleting = ref<Person | null>(null)
const deleteError = ref('')
const deleteOpen = computed({
  get: () => !!deleting.value,
  set: (value) => {
    if (!value) deleting.value = null
  },
})
function startDelete(person: Person) {
  deleting.value = person
  deleteError.value = ''
}
async function confirmDelete() {
  const person = deleting.value
  if (!person) return
  try {
    await remove.mutateAsync(person.id)
    toast.success(t('manage.people.deleted', { name: person.name }))
    deleting.value = null
  } catch (e) {
    deleteError.value = errorMessage(e, t('errors.generic'))
  }
}
</script>

<template>
  <div class="flex min-w-0 flex-1 flex-col" data-testid="PeopleView">
    <header class="flex flex-wrap items-center justify-between gap-3 border-b px-4 py-3 md:px-6">
      <div class="min-w-0">
        <h1 class="text-lg font-semibold tracking-tight">{{ t('manage.people.title') }}</h1>
        <p class="text-sm text-muted-foreground">{{ t('manage.people.subtitle') }}</p>
      </div>
      <Button v-if="editable" as-child>
        <RouterLink :to="newLink" data-testid="person-new">
          <Plus />
          {{ t('manage.people.add') }}
        </RouterLink>
      </Button>
    </header>

    <div class="p-4 md:px-6">
      <div v-if="people.isPending.value" class="flex justify-center py-10">
        <Spinner class="size-6" />
      </div>
      <Alert v-else-if="people.isError.value" variant="destructive">
        <AlertDescription>{{
          errorMessage(people.error.value, t('errors.generic'))
        }}</AlertDescription>
      </Alert>
      <Empty v-else-if="!rows.length" class="border" data-testid="people-empty">
        <EmptyHeader>
          <EmptyMedia variant="icon"><Users /></EmptyMedia>
          <EmptyTitle>{{ t('manage.people.emptyTitle') }}</EmptyTitle>
          <EmptyDescription>{{ t('manage.people.emptyHint') }}</EmptyDescription>
        </EmptyHeader>
        <EmptyContent v-if="editable">
          <Button as-child variant="outline">
            <RouterLink :to="newLink" data-testid="person-new-empty">
              <Plus />
              {{ t('manage.people.add') }}
            </RouterLink>
          </Button>
        </EmptyContent>
      </Empty>
      <ul v-else class="divide-y rounded-lg border bg-card">
        <li
          v-for="person in rows"
          :key="person.id"
          data-testid="person-row"
          class="flex flex-col gap-2 p-3 sm:flex-row sm:items-center"
        >
          <div class="min-w-0 flex-1">
            <div class="flex flex-wrap items-center gap-2">
              <span class="font-medium">{{ person.name }}</span>
              <Badge
                v-if="editable && person.open_loans"
                variant="secondary"
                class="font-mono tabular-nums"
                data-testid="person-loans"
              >
                {{ t('manage.people.openLoans', person.open_loans ?? 0) }}
              </Badge>
            </div>
            <div
              v-if="person.email"
              class="truncate font-mono text-xs text-muted-foreground"
              data-testid="person-email"
            >
              {{ person.email }}
            </div>
            <div v-if="person.notes" class="line-clamp-2 text-sm text-muted-foreground">
              {{ person.notes }}
            </div>
          </div>
          <div class="flex flex-wrap items-center gap-1">
            <Button as-child variant="ghost" size="sm">
              <RouterLink :to="explorerLink('owner', person)" data-testid="person-owned">
                {{ t('manage.people.ownedItems') }}
              </RouterLink>
            </Button>
            <Button v-if="editable" as-child variant="ghost" size="sm">
              <RouterLink :to="explorerLink('borrower', person)" data-testid="person-lent">
                {{ t('manage.people.lentItems') }}
              </RouterLink>
            </Button>
            <template v-if="editable">
              <Button as-child variant="ghost" size="icon-sm">
                <RouterLink
                  :to="editLink(person)"
                  data-testid="person-edit"
                  :aria-label="t('actions.edit')"
                >
                  <Pencil />
                </RouterLink>
              </Button>
              <Button
                variant="ghost"
                size="icon-sm"
                data-testid="person-delete"
                :aria-label="t('actions.delete')"
                @click="startDelete(person)"
              >
                <Trash2 />
              </Button>
            </template>
          </div>
        </li>
      </ul>
    </div>

    <ConfirmDialog
      v-model:open="deleteOpen"
      :title="t('manage.people.deleteTitle', { name: deleting?.name ?? '' })"
      :description="t('manage.people.deleteHint')"
      :busy="remove.isPending.value"
      :error="deleteError"
      @confirm="confirmDelete"
    />
  </div>
</template>
