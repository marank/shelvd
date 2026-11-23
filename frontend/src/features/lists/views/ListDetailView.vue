<script setup lang="ts">
import { ArrowLeft, ListChecks, Pencil, Trash2 } from '@lucide/vue'
import { toast } from 'vue-sonner'
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import { ApiError } from '@/api/errors'
import { Button } from '@/components/ui/button'
import { Empty, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from '@/components/ui/empty'
import { Skeleton } from '@/components/ui/skeleton'
import ConfirmDialog from '@/components/app/ConfirmDialog.vue'
import EntryRow from '../components/EntryRow.vue'
import PublicLinkCard from '../components/PublicLinkCard.vue'
import {
  useDeleteList,
  useEntries,
  useList,
  useMoveEntry,
  useRemoveEntry,
  useUpdateEntry,
} from '../composables/useLists'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const listId = computed(() => String(route.params.listId))

const list = useList(listId)
const entries = useEntries(listId)
const remove = useDeleteList(listId)
const updateEntry = useUpdateEntry(listId)
const moveEntry = useMoveEntry(listId)
const removeEntry = useRemoveEntry(listId)

const deleting = ref(false)
const notFound = computed(
  () => list.error.value instanceof ApiError && list.error.value.status === 404,
)
const busy = computed(() => moveEntry.isPending.value || removeEntry.isPending.value)

function fail(error: unknown) {
  toast.error(error instanceof Error ? error.message : t('errors.generic'))
}

async function destroy() {
  try {
    await remove.mutateAsync()
    deleting.value = false
    toast.success(t('lists.deleted'))
    await router.push({ name: 'lists' })
  } catch (error) {
    fail(error)
  }
}

async function saveNote(entryId: string, note: string) {
  try {
    await updateEntry.mutateAsync({ entryId, note })
    toast.success(t('lists.noteSaved'))
  } catch (error) {
    fail(error)
  }
}

async function move(index: number, delta: -1 | 1) {
  try {
    await moveEntry.mutateAsync({ entries: entries.data.value ?? [], index, delta })
  } catch (error) {
    fail(error)
  }
}

async function removeOne(entryId: string) {
  try {
    await removeEntry.mutateAsync(entryId)
    toast.success(t('lists.removed'))
  } catch (error) {
    fail(error)
  }
}
</script>

<template>
  <div
    v-if="notFound"
    class="flex flex-1 flex-col items-center justify-center gap-4 p-10 text-center"
  >
    <p class="text-muted-foreground">{{ t('lists.notFound') }}</p>
    <Button as-child variant="outline">
      <RouterLink :to="{ name: 'lists' }">{{ t('lists.backToLists') }}</RouterLink>
    </Button>
  </div>

  <template v-else>
    <header class="flex flex-wrap items-center justify-between gap-3 border-b px-4 py-3 md:px-6">
      <div class="flex min-w-0 items-start gap-2">
        <Button
          as-child
          variant="ghost"
          size="icon-sm"
          class="mt-0.5"
          :aria-label="t('lists.backToLists')"
        >
          <RouterLink :to="{ name: 'lists' }"><ArrowLeft /></RouterLink>
        </Button>
        <div class="min-w-0">
          <Skeleton v-if="list.isPending.value" class="h-6 w-48" />
          <template v-else-if="list.data.value">
            <h1 class="truncate text-lg font-semibold tracking-tight">
              {{ list.data.value.name }}
            </h1>
            <p v-if="list.data.value.description" class="text-sm text-muted-foreground">
              {{ list.data.value.description }}
            </p>
          </template>
          <p v-else class="text-sm text-destructive">{{ list.error.value?.message }}</p>
        </div>
      </div>
      <div v-if="list.data.value" class="flex gap-2">
        <Button as-child variant="outline" size="sm">
          <RouterLink :to="{ name: 'list-edit', params: { listId } }" data-testid="edit-list">
            <Pencil />
            {{ t('actions.edit') }}
          </RouterLink>
        </Button>
        <Button variant="outline" size="sm" data-testid="delete-list" @click="deleting = true">
          <Trash2 />
          {{ t('actions.delete') }}
        </Button>
      </div>
    </header>

    <div class="grid gap-6 p-4 md:px-6 lg:grid-cols-[minmax(0,1fr)_20rem] lg:items-start">
      <section class="min-w-0">
        <div v-if="entries.isPending.value" class="grid gap-3">
          <Skeleton v-for="n in 3" :key="n" class="h-14" />
        </div>
        <Empty v-else-if="!entries.data.value?.length" class="border">
          <EmptyHeader>
            <EmptyMedia variant="icon"><ListChecks /></EmptyMedia>
            <EmptyTitle>{{ t('lists.noEntriesTitle') }}</EmptyTitle>
            <EmptyDescription>{{ t('lists.noEntriesText') }}</EmptyDescription>
          </EmptyHeader>
        </Empty>
        <ol v-else class="divide-y">
          <EntryRow
            v-for="(entry, index) in entries.data.value"
            :key="entry.id"
            :entry="entry"
            :index="index"
            :first="index === 0"
            :last="index === entries.data.value.length - 1"
            :busy="busy"
            @move="(delta) => move(index, delta)"
            @remove="removeOne(entry.id)"
            @note="(note) => saveNote(entry.id, note)"
          />
        </ol>
      </section>
      <PublicLinkCard
        v-if="list.data.value"
        :list-id="listId"
        :token="list.data.value.public_token"
      />
    </div>

    <ConfirmDialog
      v-model:open="deleting"
      :title="t('lists.deleteList')"
      :description="t('lists.deleteConfirm', { name: list.data.value?.name ?? '' })"
      :busy="remove.isPending.value"
      @confirm="destroy"
    />
  </template>
</template>
