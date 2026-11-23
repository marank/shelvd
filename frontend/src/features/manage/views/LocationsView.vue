<script setup lang="ts">
import { MapPinned, Plus } from '@lucide/vue'
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { toast } from 'vue-sonner'
import { useRoute, useRouter } from 'vue-router'
import type { Location } from '@/api/types'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Empty, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from '@/components/ui/empty'
import { Input } from '@/components/ui/input'
import { Spinner } from '@/components/ui/spinner'
import { canEdit, useLibrary } from '@/features/library/composables/useLibraries'
import { useLocations } from '@/features/library/composables/useReference'
import ConfirmDialog from '@/components/app/ConfirmDialog.vue'
import LocationNode from '../components/LocationNode.vue'
import NativeSelect from '@/components/app/NativeSelect.vue'
import { errorMessage } from '../composables/format'
import { buildTree, LOCATION_KINDS, type LocationKind } from '../composables/locationTree'
import { useLocationMutations } from '../composables/useLocationMutations'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const libraryId = computed(() => String(route.params.libraryId ?? ''))
const library = useLibrary(libraryId)
const editable = computed(() => canEdit(library.data.value?.role))

const locations = useLocations(libraryId)
const all = computed(() => locations.data.value ?? [])
const tree = computed(() => buildTree(all.value))
const kindOptions = computed(() =>
  LOCATION_KINDS.map((k) => ({ value: k, label: t(`choices.location_kind.${k}`) })),
)

const collapsed = ref(new Set<string>())
function toggle(id: string) {
  const next = new Set(collapsed.value)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  collapsed.value = next
}

function showItems(location: Location) {
  void router.push({
    name: 'explorer',
    params: { libraryId: libraryId.value },
    query: { g: 'location', p: location.id },
  })
}

const { create, remove } = useLocationMutations(libraryId)

// Add (top level and inline below a node)
const newName = ref('')
const newKind = ref<LocationKind>('room')
const addingTo = ref<string | null>(null)
async function add(name: string, kind: LocationKind, parent: Location | null) {
  try {
    await create.mutateAsync({ name, kind, parent_id: parent?.id ?? null, notes: '' })
    toast.success(t('manage.locations.created', { name }))
    if (parent) {
      addingTo.value = null
      if (collapsed.value.has(parent.id)) toggle(parent.id)
    }
    return true
  } catch (e) {
    toast.error(errorMessage(e, t('errors.generic')))
    return false
  }
}
async function addTop() {
  const name = newName.value.trim()
  if (!name) return
  if (await add(name, newKind.value, null)) newName.value = ''
}

function edit(location: Location) {
  void router.push({
    name: 'location-edit',
    params: { libraryId: libraryId.value, locationId: location.id },
  })
}
const newLink = (parent?: Location) => ({
  name: 'location-new',
  params: { libraryId: libraryId.value },
  query: parent ? { parent: parent.id } : {},
})

// Delete
const deleting = ref<Location | null>(null)
const deleteError = ref('')
const deleteOpen = computed({
  get: () => !!deleting.value,
  set: (value) => {
    if (!value) deleting.value = null
  },
})
function startDelete(location: Location) {
  deleting.value = location
  deleteError.value = ''
}
async function confirmDelete() {
  const location = deleting.value
  if (!location) return
  try {
    await remove.mutateAsync(location.id)
    toast.success(t('manage.locations.deleted', { name: location.name }))
    deleting.value = null
  } catch (e) {
    deleteError.value = errorMessage(e, t('errors.generic'))
  }
}
</script>

<template>
  <div class="flex min-w-0 flex-1 flex-col" data-testid="LocationsView">
    <header class="flex flex-wrap items-center justify-between gap-3 border-b px-4 py-3 md:px-6">
      <div class="min-w-0">
        <h1 class="text-lg font-semibold tracking-tight">{{ t('manage.locations.title') }}</h1>
        <p class="text-sm text-muted-foreground">{{ t('manage.locations.subtitle') }}</p>
      </div>
      <Button v-if="editable" as-child variant="outline">
        <RouterLink :to="newLink()" data-testid="location-new">
          <Plus />
          {{ t('manage.locations.newTitle') }}
        </RouterLink>
      </Button>
    </header>

    <div class="grid gap-4 p-4 md:px-6">
      <form
        v-if="editable"
        class="flex flex-wrap items-center gap-2"
        data-testid="add-location"
        @submit.prevent="addTop"
      >
        <Input
          v-model="newName"
          class="min-w-0 flex-1 basis-48"
          :placeholder="t('manage.locations.newPlaceholder')"
          :aria-label="t('fields.name')"
          data-testid="new-location-name"
        />
        <NativeSelect
          v-model="newKind"
          :options="kindOptions"
          class="w-36"
          :aria-label="t('fields.kind')"
          data-testid="new-location-kind"
        />
        <Button type="submit" :disabled="!newName.trim() || create.isPending.value">
          <Plus />
          {{ t('manage.locations.add') }}
        </Button>
      </form>

      <div v-if="locations.isPending.value" class="flex justify-center py-10">
        <Spinner class="size-6" />
      </div>
      <Alert v-else-if="locations.isError.value" variant="destructive">
        <AlertDescription>
          {{ errorMessage(locations.error.value, t('errors.generic')) }}
        </AlertDescription>
      </Alert>
      <Empty v-else-if="!tree.length" class="border" data-testid="locations-empty">
        <EmptyHeader>
          <EmptyMedia variant="icon"><MapPinned /></EmptyMedia>
          <EmptyTitle>{{ t('manage.locations.emptyTitle') }}</EmptyTitle>
          <EmptyDescription>{{ t('manage.locations.emptyHint') }}</EmptyDescription>
        </EmptyHeader>
      </Empty>
      <ul v-else class="rounded-lg border bg-card p-1 text-sm" role="tree">
        <LocationNode
          v-for="node in tree"
          :key="node.location.id"
          :node="node"
          :depth="0"
          :editable="editable"
          :collapsed="collapsed"
          :adding-to="addingTo"
          @toggle="toggle"
          @show-items="showItems"
          :more-link="newLink"
          @edit="edit"
          @remove="startDelete"
          @start-add="addingTo = $event"
          @add-child="(parent, name) => add(name, 'box', parent)"
        />
      </ul>
    </div>

    <ConfirmDialog
      v-model:open="deleteOpen"
      :title="t('manage.locations.deleteTitle', { name: deleting?.name ?? '' })"
      :description="t('manage.locations.deleteHint')"
      :busy="remove.isPending.value"
      :error="deleteError"
      @confirm="confirmDelete"
    />
  </div>
</template>
