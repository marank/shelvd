<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import { toast } from 'vue-sonner'
import EditPage from '@/components/app/EditPage.vue'
import EditSection from '@/components/app/EditSection.vue'
import type { TakeOverIn } from '@/api/types'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Skeleton } from '@/components/ui/skeleton'
import { Textarea } from '@/components/ui/textarea'
import NativeSelect from '@/components/app/NativeSelect.vue'
import { canEdit, useLibraries } from '@/features/library/composables/useLibraries'
import ChoiceNativeSelect from '@/features/items/components/ChoiceNativeSelect.vue'
import { useLocations, usePeople } from '@/features/library/composables/useReference'
import ReleaseHeader from '../components/ReleaseHeader.vue'
import StatusBadge from '../components/StatusBadge.vue'
import { useTakeOver, useTracking } from '../composables/useWatchlist'
import { formatDay, formatPrice, today } from '../lib/format'

type Choice<K extends keyof TakeOverIn> = Exclude<TakeOverIn[K], null | undefined>

const { t, locale } = useI18n()
const route = useRoute()
const router = useRouter()
const trackingId = computed(() => String(route.params.trackingId))

const tracking = useTracking(trackingId)
const libraries = useLibraries()
const takeOver = useTakeOver()

const entry = computed(() => tracking.data.value)
const editable = computed(() => (libraries.data.value ?? []).filter((l) => canEdit(l.role)))

interface TakeOverForm {
  library_id: string
  format: Choice<'format'>
  condition: Choice<'condition'> | ''
  completeness: Choice<'completeness'> | ''
  location_id: string
  owner_id: string
  acquired_on: string
  notes: string
}

const form = reactive<TakeOverForm>({
  library_id: '',
  format: 'physical',
  condition: '',
  completeness: '',
  location_id: '',
  owner_id: '',
  acquired_on: '',
  notes: '',
})
const error = ref('')
const filled = ref(false)

// Copy defaults once both the entry and the libraries are there.
watch(
  [entry, () => libraries.data.value],
  ([value, libs]) => {
    if (filled.value || !value || !libs) return
    filled.value = true
    const target = editable.value.find((l) => l.id === value.library?.id) ?? editable.value[0]
    form.library_id = target?.id ?? ''
    form.acquired_on = value.ordered_on ?? today()
  },
  { immediate: true },
)
// Places and people belong to one library.
watch(
  () => form.library_id,
  () => {
    form.location_id = ''
    form.owner_id = ''
  },
)

const locations = useLocations(() => form.library_id)
const people = usePeople(() => form.library_id)

const price = computed(() => formatPrice(entry.value?.price, locale.value))
const carried = computed(() => {
  const value = entry.value
  if (!value) return []
  return [
    { key: 'shop', label: t('tracking.edit.shop'), value: value.shop },
    { key: 'price', label: t('tracking.edit.price'), value: price.value },
    {
      key: 'ordered',
      label: t('tracking.edit.orderedOn'),
      value: value.ordered_on ? formatDay(value.ordered_on, locale.value) : '',
    },
    { key: 'notes', label: t('tracking.edit.notes'), value: value.notes },
  ].filter((row) => row.value)
})

async function submit() {
  const value = entry.value
  if (!value || !value.is_mine || !form.library_id || takeOver.isPending.value) return
  error.value = ''
  try {
    const item = await takeOver.mutateAsync({
      id: value.id,
      body: {
        library_id: form.library_id,
        format: form.format,
        condition: form.condition || null,
        completeness: form.completeness || null,
        location_id: form.location_id || null,
        owner_id: form.owner_id || null,
        acquired_on: form.acquired_on || null,
        notes: form.notes.trim(),
      },
    })
    const library = editable.value.find((l) => l.id === form.library_id)
    toast.success(
      t('tracking.takeOverPage.done', { title: item.title, library: library?.name ?? '' }),
    )
    await router.push({ name: 'item', params: { itemId: item.id } })
  } catch (e) {
    error.value = (e as Error).message
  }
}
</script>

<template>
  <EditPage
    :title="t('tracking.takeOver')"
    :description="t('tracking.takeOverPage.description')"
    :back="{ name: 'upcoming' }"
    :busy="takeOver.isPending.value"
    :save-label="t('tracking.takeOverPage.save')"
    :error="error"
    @submit="submit"
  >
    <div v-if="tracking.isPending.value" class="py-6">
      <Skeleton class="h-28 rounded-lg" />
    </div>
    <Alert
      v-else-if="tracking.isError.value"
      variant="destructive"
      class="my-6"
      data-testid="load-error"
    >
      <AlertDescription>{{ tracking.error.value?.message }}</AlertDescription>
    </Alert>
    <template v-else-if="entry">
      <ReleaseHeader :release="entry.release" />
      <Alert v-if="!entry.is_mine" class="mb-6" data-testid="not-mine">
        <AlertDescription>{{ t('tracking.takeOverPage.notMine') }}</AlertDescription>
      </Alert>
      <Alert
        v-else-if="libraries.data.value && !editable.length"
        class="mb-6"
        data-testid="no-libraries"
      >
        <AlertDescription>{{ t('tracking.takeOverPage.noLibraries') }}</AlertDescription>
      </Alert>

      <EditSection
        :title="t('tracking.takeOverPage.target')"
        :description="t('tracking.takeOverPage.targetText')"
      >
        <div class="grid gap-1.5 sm:col-span-2">
          <Label for="take-library">{{ t('nav.library') }}</Label>
          <NativeSelect id="take-library" v-model="form.library_id" required>
            <option v-for="l in editable" :key="l.id" :value="l.id">{{ l.name }}</option>
          </NativeSelect>
        </div>
      </EditSection>

      <EditSection
        :title="t('tracking.takeOverPage.copy')"
        :description="t('tracking.takeOverPage.copyText')"
      >
        <div class="grid gap-1.5">
          <Label for="take-format">{{ t('fields.format') }}</Label>
          <ChoiceNativeSelect id="take-format" v-model="form.format" field="format" />
        </div>
        <div class="grid gap-1.5">
          <Label for="take-acquired">{{ t('fields.acquired_on') }}</Label>
          <Input id="take-acquired" v-model="form.acquired_on" type="date" />
        </div>
        <div class="grid gap-1.5">
          <Label for="take-condition">{{ t('fields.condition') }}</Label>
          <ChoiceNativeSelect
            id="take-condition"
            v-model="form.condition"
            field="condition"
            optional
          />
        </div>
        <div class="grid gap-1.5">
          <Label for="take-completeness">{{ t('fields.completeness') }}</Label>
          <ChoiceNativeSelect
            id="take-completeness"
            v-model="form.completeness"
            field="completeness"
            optional
          />
        </div>
        <div class="grid gap-1.5">
          <Label for="take-location">{{ t('fields.location') }}</Label>
          <NativeSelect id="take-location" v-model="form.location_id">
            <option value="">{{ t('common.none') }}</option>
            <option v-for="l in locations.data.value ?? []" :key="l.id" :value="l.id">
              {{ l.path }}
            </option>
          </NativeSelect>
        </div>
        <div class="grid gap-1.5">
          <Label for="take-owner">{{ t('fields.owner') }}</Label>
          <NativeSelect id="take-owner" v-model="form.owner_id">
            <option value="">{{ t('common.none') }}</option>
            <option v-for="p in people.data.value ?? []" :key="p.id" :value="p.id">
              {{ p.name }}
            </option>
          </NativeSelect>
        </div>
        <div class="grid gap-1.5 sm:col-span-2">
          <Label for="take-notes">{{ t('fields.notes') }}</Label>
          <Textarea id="take-notes" v-model="form.notes" rows="2" />
        </div>
      </EditSection>

      <EditSection
        :title="t('tracking.takeOverPage.carried')"
        :description="t('tracking.takeOverPage.carriedText')"
      >
        <dl class="grid gap-2 text-sm sm:col-span-2" data-testid="carried">
          <div class="flex items-center gap-3">
            <dt
              class="w-28 shrink-0 font-mono text-[11px] tracking-wider text-muted-foreground uppercase"
            >
              {{ t('fields.status') }}
            </dt>
            <dd><StatusBadge :status="entry.status" /></dd>
          </div>
          <div v-for="row in carried" :key="row.key" class="flex gap-3">
            <dt
              class="w-28 shrink-0 font-mono text-[11px] tracking-wider text-muted-foreground uppercase"
            >
              {{ row.label }}
            </dt>
            <dd
              class="min-w-0 break-words"
              :class="{ 'font-mono tabular': row.key !== 'notes' && row.key !== 'shop' }"
            >
              {{ row.value }}
            </dd>
          </div>
          <div v-if="!carried.length" class="text-muted-foreground">
            {{ t('tracking.takeOverPage.nothingCarried') }}
          </div>
        </dl>
      </EditSection>
    </template>
  </EditPage>
</template>
