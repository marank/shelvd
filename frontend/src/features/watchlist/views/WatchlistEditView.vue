<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter, type RouteLocationRaw } from 'vue-router'
import { toast } from 'vue-sonner'
import EditPage from '@/components/app/EditPage.vue'
import EditSection from '@/components/app/EditSection.vue'
import type { Tracking } from '@/api/types'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Skeleton } from '@/components/ui/skeleton'
import { Textarea } from '@/components/ui/textarea'
import NativeSelect from '@/components/app/NativeSelect.vue'
import { useLibraries } from '@/features/library/composables/useLibraries'
import { cn } from '@/lib/utils'
import { ExternalLink, PackageCheck, Trash2 } from '@lucide/vue'
import DatePrecisionInput from '@/components/app/DatePrecisionInput.vue'
import { Button } from '@/components/ui/button'
import { openLibrary, useCurrentLibrary } from '@/features/library/composables/useCurrentLibrary'
import ConfirmDialog from '@/components/app/ConfirmDialog.vue'
import ReleaseHeader from '../components/ReleaseHeader.vue'
import {
  TRACKING_STATUSES,
  useCreateTracking,
  useDeleteTracking,
  useRelease,
  useTracking,
  useUpdateReleaseDate,
  useUpdateTracking,
  type ReleaseDateFields,
  type TrackingStatus,
} from '../composables/useWatchlist'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()

const query = (name: string) => (typeof route.query[name] === 'string' ? route.query[name] : '')
const trackingId = computed(() => String(route.params.trackingId ?? ''))
const isNew = computed(() => !trackingId.value)

const tracking = useTracking(trackingId)
const releaseQuery = useRelease(() => (isNew.value ? query('release') : ''))
const libraries = useLibraries()
const create = useCreateTracking()
const update = useUpdateTracking()
const updateDate = useUpdateReleaseDate()
const remove = useDeleteTracking()
const removing = ref(false)

async function confirmRemove() {
  try {
    await remove.mutateAsync(trackingId.value)
    removing.value = false
    toast.success(t('tracking.delete.done'))
    await router.push(back.value)
  } catch (e) {
    error.value = (e as Error).message
  }
}
const current = useCurrentLibrary()

const release = computed(() =>
  isNew.value ? releaseQuery.data.value : tracking.data.value?.release,
)
const loading = computed(() =>
  isNew.value ? releaseQuery.isLoading.value : tracking.isPending.value,
)
const loadError = computed(() =>
  isNew.value ? releaseQuery.error.value?.message : tracking.error.value?.message,
)
const readOnly = computed(() => !isNew.value && tracking.data.value?.is_mine === false)

const back = computed<RouteLocationRaw>(() => {
  // Only paths inside the app ("//host" would leave it).
  const path = query('back')
  return /^\/(?!\/)/.test(path) ? path : { name: 'upcoming' }
})

const form = reactive<{
  status: TrackingStatus
  library_id: string
  shop: string
  price: string
  ordered_on: string
  notes: string
}>({
  status: 'watching',
  library_id: query('library'),
  shop: '',
  price: '',
  ordered_on: '',
  notes: '',
})
/** The release's date, edited here too; saved to the catalog only when it changed. */
const date = ref<ReleaseDateFields>({
  release_precision: 'tba',
  release_date: null,
  release_date_end: null,
})
const dateOf = (r: ReleaseDateFields): ReleaseDateFields => ({
  release_precision: r.release_precision,
  release_date: r.release_date,
  release_date_end: r.release_date_end,
})
watch(
  release,
  (value, previous) => value && value.id !== previous?.id && (date.value = dateOf(value)),
  { immediate: true },
)
const dateChanged = computed(
  () => !!release.value && JSON.stringify(dateOf(release.value)) !== JSON.stringify(date.value),
)
const workLink = computed(() =>
  release.value && current.id.value
    ? { name: 'work', params: { workId: release.value.work_id } }
    : null,
)
/** Libraries you can see that already own a copy: then there's nothing to take over. */
const ownedIn = computed(() => tracking.data.value?.owned_in ?? [])
const showTakeOver = computed(
  () => !isNew.value && !readOnly.value && !!release.value?.is_released && !ownedIn.value.length,
)

const error = ref('')
const busy = computed(
  () => create.isPending.value || update.isPending.value || updateDate.isPending.value,
)

function fill(entry: Tracking) {
  Object.assign(form, {
    status: entry.status,
    library_id: entry.library?.id ?? '',
    shop: entry.shop,
    price: entry.price ?? '',
    ordered_on: entry.ordered_on ?? '',
    notes: entry.notes,
  })
}
watch(
  () => tracking.data.value,
  (entry, previous) => entry && !previous && fill(entry),
  { immediate: true },
)

function body() {
  return {
    status: form.status,
    library_id: form.library_id || null,
    shop: form.shop.trim(),
    price: form.price.trim().replace(',', '.') || null,
    ordered_on: form.ordered_on || null,
    notes: form.notes.trim(),
  }
}

async function submit() {
  if (!release.value || readOnly.value || busy.value) return
  error.value = ''
  try {
    if (dateChanged.value) await updateDate.mutateAsync({ id: release.value.id, date: date.value })
    if (isNew.value) {
      await create.mutateAsync({ release_id: release.value.id, ...body() })
      toast.success(t('tracking.edit.created', { title: release.value.title }))
    } else {
      await update.mutateAsync({ id: trackingId.value, body: body() })
      toast.success(t('tracking.edit.saved'))
    }
    await router.push(back.value)
  } catch (e) {
    error.value = (e as Error).message
  }
}
</script>

<template>
  <EditPage
    :title="isNew || !release ? t('tracking.edit.newTitle') : release.title"
    :description="t('tracking.edit.description')"
    :back="back"
    :busy="busy"
    :error="error"
    @submit="submit"
  >
    <template v-if="!isNew && !readOnly" #actions>
      <Button
        type="button"
        variant="ghost"
        class="mr-auto text-destructive"
        data-testid="remove-entry"
        @click="removing = true"
      >
        <Trash2 class="size-4" /> {{ t('tracking.button.stop') }}
      </Button>
    </template>
    <div v-if="loading" class="py-6"><Skeleton class="h-28 rounded-lg" /></div>
    <Alert v-else-if="loadError" variant="destructive" class="my-6" data-testid="load-error">
      <AlertDescription>{{ loadError }}</AlertDescription>
    </Alert>
    <p v-else-if="!release" class="py-6 text-sm text-muted-foreground" data-testid="no-release">
      {{ t('tracking.edit.noRelease') }}
    </p>
    <template v-else>
      <ReleaseHeader :release="release">
        <Button v-if="workLink" as-child variant="outline" size="sm" data-testid="view-game">
          <RouterLink :to="workLink">
            <ExternalLink class="size-4" /> {{ t('tracking.viewGame') }}
          </RouterLink>
        </Button>
      </ReleaseHeader>
      <Alert v-if="ownedIn.length && !readOnly" class="mb-6" data-testid="owned">
        <AlertDescription class="flex flex-wrap items-center justify-between gap-3">
          <span>
            {{
              t('tracking.edit.owned', {
                title: release.title,
                library: ownedIn.map((l) => l.name).join(', '),
              })
            }}
          </span>
          <span class="flex flex-wrap gap-2">
            <!-- no-underline!: the alert underlines links, but these are buttons. -->
            <Button
              v-for="library in ownedIn"
              :key="library.id"
              as-child
              size="sm"
              variant="outline"
              class="no-underline!"
              :data-testid="`owned-${library.id}`"
            >
              <RouterLink
                :to="{ name: 'release', params: { releaseId: release.id } }"
                @click="openLibrary(library.id)"
              >
                <ExternalLink class="size-4" />
                {{ t('tracking.edit.viewIn', { library: library.name }) }}
              </RouterLink>
            </Button>
            <Button type="button" size="sm" data-testid="owned-remove" @click="removing = true">
              <Trash2 class="size-4" /> {{ t('tracking.button.stop') }}
            </Button>
          </span>
        </AlertDescription>
      </Alert>
      <Alert v-if="showTakeOver" class="mb-6" data-testid="released">
        <AlertDescription class="flex flex-wrap items-center justify-between gap-3">
          <span>{{ t('tracking.edit.released', { title: release.title }) }}</span>
          <Button as-child size="sm" class="no-underline!" data-testid="take-over-button">
            <RouterLink :to="{ name: 'take-over', params: { trackingId } }">
              <PackageCheck class="size-4" /> {{ t('tracking.edit.takeOver') }}
            </RouterLink>
          </Button>
        </AlertDescription>
      </Alert>
      <Alert v-if="readOnly" class="mb-6" data-testid="read-only">
        <AlertDescription>
          {{ t('tracking.edit.readOnly', { user: tracking.data.value?.user }) }}
        </AlertDescription>
      </Alert>

      <EditSection :title="t('tracking.edit.status')" :description="t('tracking.edit.statusText')">
        <div
          class="grid gap-2 sm:col-span-2 sm:grid-cols-3"
          role="radiogroup"
          :aria-label="t('tracking.edit.status')"
        >
          <label
            v-for="s in TRACKING_STATUSES"
            :key="s"
            :class="
              cn(
                'flex cursor-pointer flex-col gap-1 rounded-lg border p-3 text-sm transition-colors has-focus-visible:ring-3 has-focus-visible:ring-ring/50',
                form.status === s ? 'border-primary bg-primary/5' : 'hover:bg-muted/50',
                readOnly && 'cursor-default opacity-70',
              )
            "
          >
            <span class="flex items-center gap-2 font-medium">
              <input
                v-model="form.status"
                type="radio"
                name="status"
                class="accent-primary"
                :value="s"
                :disabled="readOnly"
                :data-testid="`status-${s}`"
              />
              {{ t(`choices.tracking.${s}`) }}
            </span>
            <span class="text-xs text-muted-foreground">{{ t(`tracking.statusHelp.${s}`) }}</span>
          </label>
        </div>
      </EditSection>

      <EditSection
        v-if="!readOnly && release?.can_edit"
        :title="t('tracking.edit.release')"
        :description="t('tracking.edit.releaseText')"
      >
        <div class="sm:col-span-2" data-testid="release-date">
          <DatePrecisionInput v-model="date" />
        </div>
      </EditSection>

      <EditSection
        :title="t('tracking.edit.purchase')"
        :description="t('tracking.edit.purchaseText')"
      >
        <div class="grid gap-1.5 sm:col-span-2">
          <Label for="tracking-shop">{{ t('tracking.edit.shop') }}</Label>
          <Input
            id="tracking-shop"
            v-model="form.shop"
            :disabled="readOnly"
            :placeholder="t('tracking.edit.shopPlaceholder')"
          />
        </div>
        <div class="grid gap-1.5">
          <Label for="tracking-price">{{ t('tracking.edit.price') }}</Label>
          <Input
            id="tracking-price"
            v-model="form.price"
            :disabled="readOnly"
            inputmode="decimal"
            class="font-mono tabular"
            placeholder="0.00"
          />
        </div>
        <div class="grid gap-1.5">
          <Label for="tracking-ordered">{{ t('tracking.edit.orderedOn') }}</Label>
          <Input id="tracking-ordered" v-model="form.ordered_on" :disabled="readOnly" type="date" />
        </div>
      </EditSection>

      <EditSection
        :title="t('tracking.edit.library')"
        :description="t('tracking.edit.libraryText')"
      >
        <div class="grid gap-1.5 sm:col-span-2">
          <Label for="tracking-library">{{ t('tracking.edit.targetLibrary') }}</Label>
          <NativeSelect id="tracking-library" v-model="form.library_id" :disabled="readOnly">
            <option value="">{{ t('tracking.edit.noLibrary') }}</option>
            <option v-for="l in libraries.data.value ?? []" :key="l.id" :value="l.id">
              {{ l.name }}
            </option>
          </NativeSelect>
        </div>
      </EditSection>

      <EditSection :title="t('tracking.edit.notes')">
        <div class="grid gap-1.5 sm:col-span-2">
          <Label for="tracking-notes" class="sr-only">{{ t('tracking.edit.notes') }}</Label>
          <Textarea id="tracking-notes" v-model="form.notes" :disabled="readOnly" rows="3" />
        </div>
      </EditSection>
    </template>
  </EditPage>
  <ConfirmDialog
    v-model:open="removing"
    :title="t('tracking.delete.title')"
    :description="t('tracking.delete.text', { title: release?.title ?? '' })"
    :busy="remove.isPending.value"
    @confirm="confirmRemove"
  />
</template>
