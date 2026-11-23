<script setup lang="ts">
import ForbiddenView from '@/features/library/views/ForbiddenView.vue'
import { useAuthStore } from '@/stores/auth'
// Entering a game no source knows. Afterwards its page offers adding a copy.
import { computed, reactive } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import { toast } from 'vue-sonner'
import DatePrecisionInput from '@/components/app/DatePrecisionInput.vue'
import EditPage from '@/components/app/EditPage.vue'
import EditSection from '@/components/app/EditSection.vue'
import NativeSelect from '@/components/app/NativeSelect.vue'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { usePlatforms } from '@/features/library/composables/useReference'
import EditionInput from '@/features/works/components/EditionInput.vue'
import TermPicker from '@/features/works/components/TermPicker.vue'
import { backTarget } from '@/features/works/composables/form'
import { termRefs, type PickedTerm } from '@/features/works/composables/useTerms'
import type { Precision } from '@/lib/releaseDate'
import { REGIONS, useCreateRelease, type Region } from '../composables/useAddApi'

const { t } = useI18n()
const auth = useAuthStore()
const route = useRoute()
const router = useRouter()
const platforms = usePlatforms()
const create = useCreateRelease()
const back = computed(() => backTarget(route.query.back))
const fromQuery = (value: unknown) => (typeof value === 'string' ? value : '')

interface ReleaseForm {
  title: string
  platform_id: string
  region: Region
  edition: string
  date: {
    release_precision: Precision
    release_date: string | null
    release_date_end: string | null
  }
  publisher: PickedTerm[]
  series: PickedTerm[]
  franchises: PickedTerm[]
  developers: PickedTerm[]
  genres: PickedTerm[]
  summary: string
  barcode: string
}

const form = reactive<ReleaseForm>({
  title: fromQuery(route.query.title),
  platform_id: '',
  region: 'pal',
  edition: '',
  date: { release_precision: 'day', release_date: null, release_date_end: null },
  publisher: [],
  series: [],
  franchises: [],
  developers: [],
  genres: [],
  summary: '',
  barcode: fromQuery(route.query.barcode),
})
const valid = computed(() => !!form.title.trim() && !!form.platform_id)

function save() {
  if (!valid.value || create.isPending.value) return
  create.mutate(
    {
      title: form.title.trim(),
      platform_id: form.platform_id,
      region: form.region,
      edition: form.edition.trim(),
      release_precision: form.date.release_precision,
      release_date: form.date.release_date,
      release_date_end: form.date.release_date_end,
      publisher: termRefs(form.publisher)[0] ?? null,
      series: termRefs(form.series),
      franchises: termRefs(form.franchises),
      developers: termRefs(form.developers),
      genres: termRefs(form.genres),
      summary: form.summary.trim(),
      barcode: form.barcode.replace(/\s+/g, '') || null,
    },
    {
      onSuccess: (release) => {
        toast.success(t('add.manual.created', { title: release.title }))
        void router.replace({ name: 'release', params: { releaseId: release.id } })
      },
    },
  )
}
</script>

<template>
  <ForbiddenView v-if="!auth.canContribute" />
  <EditPage
    v-else
    :title="t('add.manual.title')"
    :description="t('add.manual.intro')"
    :back="back"
    :busy="create.isPending.value"
    :save-label="t('add.manual.create')"
    :error="create.error.value?.message"
    @submit="save"
  >
    <EditSection :title="t('add.manual.game')">
      <div class="grid gap-1.5 sm:col-span-2">
        <Label for="manual-title">{{ t('fields.title') }} *</Label>
        <Input id="manual-title" v-model="form.title" required autocomplete="off" />
      </div>
      <div class="grid gap-1.5">
        <Label for="manual-platform">{{ t('fields.platform') }} *</Label>
        <NativeSelect id="manual-platform" v-model="form.platform_id" required>
          <option value="" disabled>{{ t('add.choose') }}</option>
          <option v-for="p in platforms.data.value ?? []" :key="p.id" :value="p.id">
            {{ p.name }}
          </option>
        </NativeSelect>
      </div>
      <div class="grid gap-1.5">
        <Label for="manual-region">{{ t('fields.region') }}</Label>
        <NativeSelect id="manual-region" v-model="form.region">
          <option v-for="r in REGIONS" :key="r" :value="r">{{ t(`choices.region.${r}`) }}</option>
        </NativeSelect>
      </div>
      <div class="grid gap-1.5">
        <Label for="manual-edition">{{ t('fields.edition') }}</Label>
        <EditionInput
          id="manual-edition"
          v-model="form.edition"
          :placeholder="t('add.manual.editionHint')"
        />
      </div>
      <div class="grid gap-1.5">
        <Label for="manual-barcode">{{ t('fields.barcode') }}</Label>
        <Input
          id="manual-barcode"
          v-model="form.barcode"
          autocapitalize="characters"
          spellcheck="false"
          class="font-mono tabular-nums"
        />
      </div>
      <div class="grid gap-1.5 sm:col-span-2">
        <span class="text-sm font-medium">{{ t('fields.release_date') }}</span>
        <DatePrecisionInput v-model="form.date" />
      </div>
    </EditSection>
    <EditSection :title="t('add.manual.details')">
      <div class="grid gap-1.5">
        <Label for="manual-publisher">{{ t('fields.publisher') }}</Label>
        <TermPicker id="manual-publisher" v-model="form.publisher" kind="companies" />
      </div>
      <div class="grid gap-1.5">
        <Label for="manual-developers">{{ t('fields.developers') }}</Label>
        <TermPicker id="manual-developers" v-model="form.developers" kind="companies" multiple />
      </div>
      <div class="grid gap-1.5">
        <Label for="manual-genres">{{ t('fields.genres') }}</Label>
        <TermPicker id="manual-genres" v-model="form.genres" kind="genres" multiple />
      </div>
      <div class="grid gap-1.5">
        <Label for="manual-franchises">{{ t('fields.franchises') }}</Label>
        <TermPicker id="manual-franchises" v-model="form.franchises" kind="franchises" multiple />
      </div>
      <div class="grid gap-1.5">
        <Label for="manual-series">{{ t('fields.series') }}</Label>
        <TermPicker id="manual-series" v-model="form.series" kind="series" multiple />
      </div>
      <div class="grid gap-1.5 sm:col-span-2">
        <Label for="manual-summary">{{ t('fields.summary') }}</Label>
        <Textarea id="manual-summary" v-model="form.summary" rows="3" />
      </div>
    </EditSection>
  </EditPage>
</template>
