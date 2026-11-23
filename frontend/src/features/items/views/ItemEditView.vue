<script setup lang="ts">
import { Image as ImageIcon, ImageOff, ImageUp, RotateCcw } from '@lucide/vue'
import { computed, reactive, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import { toast } from 'vue-sonner'
import CoverImage from '@/components/app/CoverImage.vue'
import DatePrecisionInput from '@/components/app/DatePrecisionInput.vue'
import ReleaseDate from '@/components/app/ReleaseDate.vue'
import EditPage from '@/components/app/EditPage.vue'
import EditSection from '@/components/app/EditSection.vue'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import type { ItemPatch, Release } from '@/api/types'
import { canEdit, useLibrary } from '@/features/library/composables/useLibraries'
import ForbiddenView from '@/features/library/views/ForbiddenView.vue'
import { useLocations, usePeople } from '@/features/library/composables/useReference'
import ChoiceSelect from '../components/ChoiceSelect.vue'
import { useChoiceOptions } from '../components/options'
import { useItemById, useItemMutations, useRelease } from '../composables/useItem'
import { splitList } from '@/features/works/composables/form'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const itemId = computed(() => String(route.params.itemId))
const { item, libraryId } = useItemById(itemId)
const locations = useLocations(libraryId)
const people = usePeople(libraryId)
const options = useChoiceOptions()
const { update, uploadCover, removeCover, reset } = useItemMutations(libraryId)
const library = useLibrary(libraryId)
const editable = computed(() => canEdit(library.data.value?.role))
// The catalog's values, to show beside the copy's own (the copy shows its own ones).
const catalog = useRelease(() => item.data.value?.release.id ?? '')

const back = computed(() => ({ name: 'item', params: { itemId: itemId.value } }))

type DateValue = {
  release_precision: Release['release_precision']
  release_date: string | null
  release_date_end: string | null
}
const ownDate = ref(false)
const date = ref<DateValue>({
  release_precision: 'day',
  release_date: null,
  release_date_end: null,
})

type Choice = string | null
interface CopyForm {
  title_override: string
  edition_override: string
  region_override: Choice
  format: Choice
  status: Choice
  condition: Choice
  completeness: Choice
  play_status: Choice
  location_id: string | null
  owner_id: string | null
  acquired_on: string
  purchase_price: string
  current_value: string
  tags: string
  notes: string
}

const form = reactive<CopyForm>({
  title_override: '',
  edition_override: '',
  region_override: null,
  format: 'physical',
  status: 'owned',
  condition: null,
  completeness: null,
  play_status: null,
  location_id: null,
  owner_id: null,
  acquired_on: '',
  purchase_price: '',
  current_value: '',
  tags: '',
  notes: '',
})
const loaded = ref(false)
watch(
  () => item.data.value,
  (value) => {
    if (!value || loaded.value) return
    loaded.value = true
    ownDate.value = !!value.release_precision_override
    if (value.release_precision_override) {
      date.value = {
        release_precision: value.release_precision_override,
        release_date: value.release_date_override,
        release_date_end: value.release_date_end_override,
      }
    }
    Object.assign(form, {
      title_override: value.title_override,
      edition_override: value.edition_override,
      region_override: value.region_override,
      format: value.format,
      status: value.status,
      condition: value.condition,
      completeness: value.completeness,
      play_status: value.play_status,
      location_id: value.location?.id ?? null,
      owner_id: value.owner?.id ?? null,
      acquired_on: value.acquired_on ?? '',
      purchase_price: value.purchase_price ?? '',
      current_value: value.current_value ?? '',
      tags: value.tags.join(', '),
      notes: value.notes,
    })
  },
  { immediate: true },
)

const locationOptions = computed(() =>
  (locations.data.value ?? []).map((l) => ({ value: l.id, label: l.path })),
)
const peopleOptions = computed(() =>
  (people.data.value ?? []).map((p) => ({ value: p.id, label: p.name })),
)
const error = ref('')
const fileInput = ref<HTMLInputElement | null>(null)

async function save() {
  error.value = ''
  const body = {
    ...form,
    title_override: form.title_override.trim(),
    edition_override: form.edition_override.trim(),
    region_override: form.region_override ?? '',
    release_precision_override: ownDate.value ? date.value.release_precision : '',
    release_date_override: ownDate.value ? date.value.release_date : null,
    release_date_end_override: ownDate.value ? date.value.release_date_end : null,
    acquired_on: form.acquired_on || null,
    purchase_price: form.purchase_price === '' ? null : String(form.purchase_price),
    current_value: form.current_value === '' ? null : String(form.current_value),
    tags: splitList(form.tags),
  } as ItemPatch
  try {
    await update.mutateAsync({ id: itemId.value, body })
    toast.success(t('items.saved'))
    void router.push(back.value)
  } catch (e) {
    error.value = e instanceof Error ? e.message : t('errors.generic')
  }
}

async function upload(event: Event) {
  const file = (event.target as HTMLInputElement).files?.[0]
  if (!file) return
  try {
    await uploadCover.mutateAsync({ id: itemId.value, file })
    toast.success(t('items.coverUploaded'))
  } catch (e) {
    error.value = e instanceof Error ? e.message : t('errors.generic')
  }
}

/** Back to the release's value for one field (saved with the form). */
function useCatalog(field: 'title' | 'edition' | 'region' | 'release_date') {
  if (field === 'title') form.title_override = ''
  if (field === 'edition') form.edition_override = ''
  if (field === 'region') form.region_override = null
  if (field === 'release_date') ownDate.value = false
}

const differs = computed(() => ({
  title: !!form.title_override.trim(),
  edition: !!form.edition_override.trim(),
  region: !!form.region_override,
  release_date: ownDate.value,
}))

async function resetAll() {
  await reset.mutateAsync(itemId.value)
  toast.success(t('items.overrides.resetDone'))
  void router.push(back.value)
}

async function resetCover() {
  await removeCover.mutateAsync(itemId.value)
  toast.success(t('items.coverReset'))
}
</script>

<template>
  <ForbiddenView v-if="item.data.value && library.data.value && !editable" />
  <EditPage
    v-else-if="item.data.value"
    :title="t('items.editCopy')"
    :description="item.data.value.title"
    :back="back"
    :busy="update.isPending.value"
    :error="error"
    @submit="save"
  >
    <EditSection :title="t('items.overrides.title')" :description="t('items.overrides.hint')">
      <div class="grid gap-1.5 sm:col-span-2">
        <Label for="f-title">{{ t('fields.title') }}</Label>
        <div class="flex gap-2">
          <Input
            id="f-title"
            v-model="form.title_override"
            :placeholder="catalog.data.value?.title"
          />
          <Button
            v-if="differs.title"
            type="button"
            variant="ghost"
            size="icon"
            :aria-label="t('items.overrides.useCatalog')"
            :title="t('items.overrides.useCatalog')"
            data-testid="reset-title"
            @click="useCatalog('title')"
          >
            <RotateCcw class="size-4" />
          </Button>
        </div>
      </div>
      <div class="grid gap-1.5">
        <Label for="f-edition">{{ t('fields.edition') }}</Label>
        <div class="flex gap-2">
          <Input
            id="f-edition"
            v-model="form.edition_override"
            :placeholder="catalog.data.value?.edition || t('items.overrides.none')"
          />
          <Button
            v-if="differs.edition"
            type="button"
            variant="ghost"
            size="icon"
            :aria-label="t('items.overrides.useCatalog')"
            data-testid="reset-edition"
            @click="useCatalog('edition')"
          >
            <RotateCcw class="size-4" />
          </Button>
        </div>
      </div>
      <div class="grid gap-1.5">
        <Label for="f-region">{{ t('fields.region') }}</Label>
        <ChoiceSelect
          id="f-region"
          v-model="form.region_override"
          optional
          :options="options('region')"
        />
        <p v-if="catalog.data.value" class="text-xs text-muted-foreground">
          {{ t('items.overrides.catalog') }}:
          {{ t(`choices.region.${catalog.data.value.region}`) }}
        </p>
      </div>
      <div class="grid gap-1.5 sm:col-span-2">
        <label class="flex items-center gap-2 text-sm font-medium">
          <input v-model="ownDate" type="checkbox" class="size-4" data-testid="own-date" />
          {{ t('items.overrides.ownDate') }}
        </label>
        <DatePrecisionInput v-if="ownDate" v-model="date" />
        <p v-if="catalog.data.value" class="text-xs text-muted-foreground">
          {{ t('items.overrides.catalog') }}:
          <ReleaseDate :release="catalog.data.value" />
        </p>
      </div>
      <div class="flex items-end gap-4 sm:col-span-2">
        <CoverImage
          :aspect="item.data.value.cover_aspect"
          :src="item.data.value.cover_url"
          :title="item.data.value.title"
          :manufacturer="item.data.value.release.platform.manufacturer"
          class="w-24"
        />
        <div class="flex flex-col gap-2">
          <input
            ref="fileInput"
            type="file"
            accept="image/jpeg,image/png,image/webp"
            class="hidden"
            :aria-label="t('items.ownCover')"
            data-testid="cover-input"
            @change="upload"
          />
          <Button type="button" size="sm" variant="outline" @click="fileInput?.click()">
            <ImageUp class="size-4" /> {{ t('items.ownCover') }}
          </Button>
          <Button as-child type="button" size="sm" variant="outline" data-testid="find-cover">
            <RouterLink
              :to="{
                name: 'cover-search',
                params: { releaseId: item.data.value.release.id },
                query: { back: $route.fullPath, item: itemId },
              }"
            >
              <ImageIcon class="size-4" /> {{ t('integrations.covers.search') }}
            </RouterLink>
          </Button>
          <Button
            v-if="item.data.value.has_cover_override"
            type="button"
            size="sm"
            variant="ghost"
            data-testid="reset-cover"
            @click="resetCover"
          >
            <ImageOff class="size-4" /> {{ t('items.catalogCover') }}
          </Button>
        </div>
      </div>
    </EditSection>

    <div
      v-if="item.data.value.overrides.length"
      class="flex flex-wrap items-center justify-between gap-2 py-4"
      data-testid="overrides"
    >
      <p class="text-sm text-muted-foreground">
        {{
          t('items.overrides.current', {
            fields: item.data.value.overrides
              .map((f) => t(`items.overrides.fields.${f}`))
              .join(', '),
          })
        }}
      </p>
      <Button
        type="button"
        variant="outline"
        size="sm"
        :disabled="reset.isPending.value"
        data-testid="reset-all"
        @click="resetAll"
      >
        <RotateCcw class="size-4" /> {{ t('items.overrides.resetAll') }}
      </Button>
    </div>

    <EditSection :title="t('items.thisCopy')">
      <div class="grid gap-1.5">
        <Label for="f-format">{{ t('fields.format') }}</Label>
        <ChoiceSelect id="f-format" v-model="form.format" :options="options('format')" />
      </div>
      <div class="grid gap-1.5">
        <Label for="f-status">{{ t('fields.status') }}</Label>
        <ChoiceSelect id="f-status" v-model="form.status" :options="options('status')" />
      </div>
      <div class="grid gap-1.5">
        <Label for="f-condition">{{ t('fields.condition') }}</Label>
        <ChoiceSelect
          id="f-condition"
          v-model="form.condition"
          optional
          :options="options('condition')"
        />
      </div>
      <div class="grid gap-1.5">
        <Label for="f-completeness">{{ t('fields.completeness') }}</Label>
        <ChoiceSelect
          id="f-completeness"
          v-model="form.completeness"
          optional
          :options="options('completeness')"
        />
      </div>
      <div class="grid gap-1.5">
        <Label for="f-play">{{ t('fields.play_status') }}</Label>
        <ChoiceSelect
          id="f-play"
          v-model="form.play_status"
          optional
          :options="options('play_status')"
        />
      </div>
      <div class="grid gap-1.5 sm:col-span-2">
        <Label for="f-tags">{{ t('fields.tags') }}</Label>
        <Input id="f-tags" v-model="form.tags" :placeholder="t('items.tagsHint')" />
      </div>
    </EditSection>

    <EditSection :title="t('items.placeAndOwner')" :description="t('items.placeAndOwnerHint')">
      <div class="grid gap-1.5">
        <Label for="f-location">{{ t('fields.location') }}</Label>
        <ChoiceSelect
          id="f-location"
          v-model="form.location_id"
          optional
          :options="locationOptions"
        />
      </div>
      <div class="grid gap-1.5">
        <Label for="f-owner">{{ t('fields.owner') }}</Label>
        <ChoiceSelect id="f-owner" v-model="form.owner_id" optional :options="peopleOptions" />
      </div>
    </EditSection>

    <EditSection :title="t('items.purchase')" :description="t('items.valueHint')">
      <div class="grid gap-1.5">
        <Label for="f-acquired">{{ t('fields.acquired_on') }}</Label>
        <Input id="f-acquired" v-model="form.acquired_on" type="date" />
      </div>
      <div class="grid gap-1.5">
        <Label for="f-price">{{ t('fields.purchase_price') }}</Label>
        <Input
          id="f-price"
          v-model="form.purchase_price"
          type="number"
          min="0"
          step="0.01"
          inputmode="decimal"
        />
      </div>
      <div class="grid gap-1.5">
        <Label for="f-value">{{ t('fields.current_value') }}</Label>
        <Input
          id="f-value"
          v-model="form.current_value"
          type="number"
          min="0"
          step="0.01"
          inputmode="decimal"
        />
      </div>
      <div class="grid gap-1.5 sm:col-span-2">
        <Label for="f-notes">{{ t('fields.notes') }}</Label>
        <Textarea id="f-notes" v-model="form.notes" rows="4" />
      </div>
    </EditSection>
  </EditPage>
</template>
