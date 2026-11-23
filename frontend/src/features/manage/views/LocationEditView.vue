<script setup lang="ts">
import { ListTree, Trash2 } from '@lucide/vue'
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { toast } from 'vue-sonner'
import { useRoute, useRouter } from 'vue-router'
import EditPage from '@/components/app/EditPage.vue'
import EditSection from '@/components/app/EditSection.vue'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Spinner } from '@/components/ui/spinner'
import { Textarea } from '@/components/ui/textarea'
import { canEdit, useLibrary } from '@/features/library/composables/useLibraries'
import { useLocations } from '@/features/library/composables/useReference'
import { cn } from '@/lib/utils'
import ConfirmDialog from '@/components/app/ConfirmDialog.vue'
import NativeSelect from '@/components/app/NativeSelect.vue'
import { errorMessage } from '../composables/format'
import {
  KIND_ICONS,
  LOCATION_KINDS,
  subtreeIds,
  type LocationKind,
} from '../composables/locationTree'
import { useLocationMutations } from '../composables/useLocationMutations'

/** Create (route location-new, ?parent=<id>) or edit (location-edit) one place. */
const ROOT = ''

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const libraryId = computed(() => String(route.params.libraryId ?? ''))
const locationId = computed(() => (route.params.locationId as string | undefined) ?? '')
const isNew = computed(() => !locationId.value)
const library = useLibrary(libraryId)
const editable = computed(() => canEdit(library.data.value?.role))

const locations = useLocations(libraryId)
const all = computed(() => locations.data.value ?? [])
const location = computed(() => all.value.find((l) => l.id === locationId.value))
const notFound = computed(() => !isNew.value && locations.isSuccess.value && !location.value)

const back = computed(() => ({ name: 'locations', params: { libraryId: libraryId.value } }))

const form = ref<{ name: string; kind: LocationKind; parent: string; notes: string }>({
  name: '',
  kind: 'room',
  parent: ROOT,
  notes: '',
})
const loaded = ref(false)
watch([locationId, () => route.query.parent], () => (loaded.value = false))
watch(
  [locations.data, location, loaded],
  () => {
    if (loaded.value || !locations.data.value) return
    if (isNew.value) {
      const parent = String(route.query.parent ?? '')
      const known = all.value.some((l) => l.id === parent)
      form.value = {
        name: '',
        kind: known ? 'box' : 'room',
        parent: known ? parent : ROOT,
        notes: '',
      }
    } else if (location.value) {
      form.value = {
        name: location.value.name,
        kind: location.value.kind,
        parent: location.value.parent_id ?? ROOT,
        notes: location.value.notes,
      }
    } else return
    loaded.value = true
  },
  { immediate: true },
)

const kinds = computed(() =>
  LOCATION_KINDS.map((k) => ({
    value: k,
    label: t(`choices.location_kind.${k}`),
    icon: KIND_ICONS[k],
  })),
)
const parentOptions = computed(() => {
  const blocked = isNew.value ? new Set<string>() : subtreeIds(all.value, locationId.value)
  return [
    { value: ROOT, label: t('manage.locations.topLevel') },
    ...all.value
      .filter((l) => !blocked.has(l.id))
      .map((l) => ({ value: l.id, label: l.path || l.name }))
      .sort((a, b) => a.label.localeCompare(b.label)),
  ]
})

const { create, update, remove } = useLocationMutations(libraryId)
const busy = computed(() => create.isPending.value || update.isPending.value)
const error = ref('')

async function save() {
  if (!editable.value) {
    error.value = t('manage.readOnly')
    return
  }
  const name = form.value.name.trim()
  if (!name) {
    error.value = t('manage.locations.nameRequired')
    return
  }
  error.value = ''
  const body = {
    name,
    kind: form.value.kind,
    parent_id: form.value.parent || null,
    notes: form.value.notes,
  }
  try {
    if (isNew.value) {
      await create.mutateAsync(body)
      toast.success(t('manage.locations.created', { name }))
    } else {
      await update.mutateAsync({ id: locationId.value, body })
      toast.success(t('manage.locations.saved'))
    }
    await router.push(back.value)
  } catch (e) {
    error.value = errorMessage(e, t('errors.generic'))
  }
}

const itemsLink = computed(() => ({
  name: 'explorer',
  params: { libraryId: libraryId.value },
  query: { g: 'location', p: locationId.value },
}))

const deleteOpen = ref(false)
const deleteError = ref('')
function startDelete() {
  deleteError.value = ''
  deleteOpen.value = true
}
async function confirmDelete() {
  const name = location.value?.name ?? ''
  try {
    await remove.mutateAsync(locationId.value)
    toast.success(t('manage.locations.deleted', { name }))
    deleteOpen.value = false
    await router.push(back.value)
  } catch (e) {
    deleteError.value = errorMessage(e, t('errors.generic'))
  }
}
</script>

<template>
  <div class="flex min-h-0 min-w-0 flex-1 flex-col" data-testid="LocationEditView">
    <div v-if="locations.isPending.value" class="flex justify-center py-10">
      <Spinner class="size-6" />
    </div>
    <div v-else-if="locations.isError.value || notFound" class="p-4 md:px-6">
      <Alert variant="destructive">
        <AlertDescription data-testid="location-load-error">
          {{
            notFound
              ? t('manage.locations.notFound')
              : errorMessage(locations.error.value, t('errors.generic'))
          }}
        </AlertDescription>
      </Alert>
      <Button as-child variant="outline" class="mt-4">
        <RouterLink :to="back">{{ t('manage.locations.title') }}</RouterLink>
      </Button>
    </div>
    <EditPage
      v-else
      :title="isNew ? t('manage.locations.newTitle') : t('manage.locations.editTitle')"
      :description="isNew ? t('manage.locations.subtitle') : location?.path"
      :back="back"
      :busy="busy"
      :save-label="isNew ? t('actions.create') : t('actions.save')"
      :error="error"
      @submit="save"
    >
      <EditSection
        :title="t('manage.locations.general')"
        :description="t('manage.locations.generalHint')"
      >
        <div class="grid gap-1.5 sm:col-span-2">
          <Label for="location-name">{{ t('fields.name') }}</Label>
          <Input
            id="location-name"
            v-model="form.name"
            required
            :placeholder="t('manage.locations.newPlaceholder')"
          />
        </div>
        <fieldset class="grid gap-1.5 sm:col-span-2">
          <legend class="mb-1.5 text-sm leading-none font-medium">{{ t('fields.kind') }}</legend>
          <div class="grid grid-cols-2 gap-2 sm:grid-cols-5" role="radiogroup">
            <label
              v-for="kind in kinds"
              :key="kind.value"
              :class="
                cn(
                  'flex cursor-pointer flex-col items-center gap-1.5 rounded-lg border bg-card px-2 py-3 text-sm transition-colors hover:bg-muted/50 has-focus-visible:ring-3 has-focus-visible:ring-ring/50',
                  form.kind === kind.value && 'border-primary bg-primary/5 font-medium',
                )
              "
              :data-testid="`kind-${kind.value}`"
            >
              <input
                v-model="form.kind"
                type="radio"
                name="location-kind"
                class="sr-only"
                :value="kind.value"
              />
              <component :is="kind.icon" class="size-5 text-muted-foreground" />
              {{ kind.label }}
            </label>
          </div>
        </fieldset>
      </EditSection>

      <EditSection :title="t('fields.parent')" :description="t('manage.locations.parentHint')">
        <div class="grid gap-1.5 sm:col-span-2">
          <Label for="location-parent">{{ t('fields.parent') }}</Label>
          <NativeSelect id="location-parent" v-model="form.parent" :options="parentOptions" />
        </div>
        <div class="grid gap-1.5 sm:col-span-2">
          <Label for="location-notes">
            {{ t('fields.notes') }}
            <span class="text-muted-foreground">({{ t('common.optional') }})</span>
          </Label>
          <Textarea id="location-notes" v-model="form.notes" rows="3" />
        </div>
      </EditSection>

      <EditSection v-if="location" :title="t('manage.locations.info')">
        <dl class="grid gap-3 sm:col-span-2 sm:grid-cols-2">
          <div>
            <dt class="font-mono text-[11px] tracking-wider text-muted-foreground uppercase">
              {{ t('manage.locations.path') }}
            </dt>
            <dd data-testid="location-path">{{ location.path || location.name }}</dd>
          </div>
          <div>
            <dt class="font-mono text-[11px] tracking-wider text-muted-foreground uppercase">
              {{ t('manage.locations.directItems') }}
            </dt>
            <dd class="font-mono tabular-nums" data-testid="location-count">
              {{ t('common.items', location.item_count ?? 0) }}
            </dd>
          </div>
        </dl>
        <div class="flex flex-wrap gap-2 sm:col-span-2">
          <Button as-child variant="outline" size="sm">
            <RouterLink :to="itemsLink" data-testid="location-items">
              <ListTree />
              {{ t('manage.locations.showItems') }}
            </RouterLink>
          </Button>
        </div>
      </EditSection>

      <template v-if="location && editable" #actions>
        <Button
          type="button"
          variant="ghost"
          class="text-destructive"
          data-testid="location-delete"
          @click="startDelete"
        >
          <Trash2 />
          <span class="hidden sm:inline">{{ t('actions.delete') }}</span>
        </Button>
      </template>
    </EditPage>

    <ConfirmDialog
      v-model:open="deleteOpen"
      :title="t('manage.locations.deleteTitle', { name: location?.name ?? '' })"
      :description="t('manage.locations.deleteHint')"
      :busy="remove.isPending.value"
      :error="deleteError"
      @confirm="confirmDelete"
    />
  </div>
</template>
