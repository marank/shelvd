<script setup lang="ts">
import ForbiddenView from '@/features/library/views/ForbiddenView.vue'
import { useAuthStore } from '@/stores/auth'
import { ImageUp, Image as ImageIcon, Info } from '@lucide/vue'
import { computed, reactive, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import { toast } from 'vue-sonner'
import CoverImage from '@/components/app/CoverImage.vue'
import DatePrecisionInput from '@/components/app/DatePrecisionInput.vue'
import EditPage from '@/components/app/EditPage.vue'
import EditSection from '@/components/app/EditSection.vue'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import type { Release, ReleasePatch } from '@/api/types'
import ChoiceSelect from '@/features/items/components/ChoiceSelect.vue'
import { useChoiceOptions } from '@/features/items/components/options'
import { useRelease, useReleaseMutations } from '@/features/items/composables/useItem'
import { useCurrentLibrary } from '@/features/library/composables/useCurrentLibrary'
import { usePlatforms } from '@/features/library/composables/useReference'
import EditionInput from '../components/EditionInput.vue'
import TermPicker from '../components/TermPicker.vue'
import { backTarget } from '../composables/form'
import { termRefs, type PickedTerm } from '../composables/useTerms'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const releaseId = computed(() => String(route.params.releaseId))
const release = useRelease(releaseId)
const auth = useAuthStore()
const platforms = usePlatforms()
const options = useChoiceOptions()
const { id: libraryId } = useCurrentLibrary()
const { update, uploadCover, addBarcode } = useReleaseMutations(libraryId)
const back = computed(() => backTarget(route.query.back))

interface ReleaseForm {
  title: string
  platform_id: string | null
  region: string | null
  edition: string
  publisher: PickedTerm[]
  release_developers: PickedTerm[]
  age_rating: string
  product_code: string
  release_number: string | number
}

const form = reactive<ReleaseForm>({
  title: '',
  platform_id: '',
  region: 'pal',
  edition: '',
  publisher: [],
  release_developers: [],
  age_rating: '',
  product_code: '',
  release_number: '',
})
const date = ref<{
  release_precision: Release['release_precision']
  release_date: string | null
  release_date_end: string | null
}>({
  release_precision: 'day',
  release_date: null as string | null,
  release_date_end: null as string | null,
})
const barcode = ref('')
const loaded = ref(false)
watch(
  () => release.data.value,
  (value) => {
    if (!value || loaded.value) return
    loaded.value = true
    Object.assign(form, {
      title: value.title,
      platform_id: value.platform.id,
      region: value.region,
      edition: value.edition,
      publisher: value.publisher ? [value.publisher] : [],
      release_developers: [...value.release_developers],
      age_rating: value.age_rating,
      product_code: value.product_code,
      release_number: value.release_number ?? '',
    })
    date.value = {
      release_precision: value.release_precision,
      release_date: value.release_date,
      release_date_end: value.release_date_end,
    }
  },
  { immediate: true },
)
const platformOptions = computed(() =>
  (platforms.data.value ?? []).map((p) => ({ value: p.id, label: p.name })),
)
const error = ref('')
const fileInput = ref<HTMLInputElement | null>(null)

function fail(e: unknown) {
  error.value = e instanceof Error ? e.message : t('errors.generic')
}

async function save() {
  error.value = ''
  try {
    const number = form.release_number === '' ? null : Number(form.release_number)
    await update.mutateAsync({
      id: releaseId.value,
      body: {
        ...form,
        publisher: termRefs(form.publisher)[0] ?? null,
        release_developers: termRefs(form.release_developers),
        release_number: number,
        ...date.value,
      } as ReleasePatch,
    })
    if (barcode.value.trim())
      await addBarcode.mutateAsync({ id: releaseId.value, code: barcode.value.trim() })
    toast.success(t('items.saved'))
    void router.push(back.value)
  } catch (e) {
    fail(e)
  }
}

async function upload(event: Event) {
  const file = (event.target as HTMLInputElement).files?.[0]
  if (!file) return
  try {
    await uploadCover.mutateAsync({ id: releaseId.value, file })
    toast.success(t('items.coverUploaded'))
  } catch (e) {
    fail(e)
  }
}
</script>

<template>
  <ForbiddenView v-if="release.data.value && !release.data.value.can_edit" />
  <EditPage
    v-else-if="release.data.value"
    :title="t('works.editRelease')"
    :description="`${release.data.value.work_title} · ${release.data.value.platform.name}`"
    :back="back"
    :busy="update.isPending.value"
    :error="error"
    @submit="save"
  >
    <Alert class="my-4 border-primary/30 bg-primary/5">
      <Info class="size-4" />
      <AlertDescription>{{ t('works.catalogHint') }}</AlertDescription>
    </Alert>
    <EditSection :title="t('works.release')" :description="t('works.releaseHint')">
      <div class="grid gap-1.5 sm:col-span-2">
        <Label for="r-title">{{ t('works.regionalTitle') }}</Label>
        <Input id="r-title" v-model="form.title" />
      </div>
      <div class="grid gap-1.5">
        <Label for="r-platform">{{ t('fields.platform') }}</Label>
        <ChoiceSelect id="r-platform" v-model="form.platform_id" :options="platformOptions" />
      </div>
      <div class="grid gap-1.5">
        <Label for="r-region">{{ t('fields.region') }}</Label>
        <ChoiceSelect id="r-region" v-model="form.region" :options="options('region')" />
      </div>
      <div class="grid gap-1.5">
        <Label for="r-edition">{{ t('fields.edition') }}</Label>
        <EditionInput id="r-edition" v-model="form.edition" />
      </div>
      <div class="grid gap-1.5">
        <Label for="r-publisher">{{ t('fields.publisher') }}</Label>
        <TermPicker id="r-publisher" v-model="form.publisher" kind="companies" />
      </div>
      <div class="grid gap-1.5">
        <Label for="r-developers">{{ t('works.releaseDevelopers') }}</Label>
        <TermPicker id="r-developers" v-model="form.release_developers" kind="companies" multiple />
        <p class="text-xs text-muted-foreground">{{ t('works.releaseDevelopersHint') }}</p>
      </div>
      <div class="grid gap-1.5">
        <Label for="r-age">{{ t('fields.age_rating') }}</Label>
        <Input id="r-age" v-model="form.age_rating" placeholder="USK 12" />
      </div>
      <div class="grid gap-1.5">
        <Label for="r-code">{{ t('fields.product_code') }}</Label>
        <Input
          id="r-code"
          v-model="form.product_code"
          class="font-mono"
          placeholder="LA-H-AAAAA-EUR"
        />
      </div>
      <div class="grid gap-1.5">
        <Label for="r-number">{{ t('fields.release_number') }}</Label>
        <Input
          id="r-number"
          v-model="form.release_number"
          type="number"
          min="1"
          inputmode="numeric"
        />
      </div>
    </EditSection>
    <EditSection :title="t('fields.release_date')" :description="t('works.dateHint')">
      <div class="sm:col-span-2">
        <DatePrecisionInput v-model="date" />
      </div>
    </EditSection>
    <EditSection :title="t('fields.cover')" :description="t('works.coverHint')">
      <div class="flex items-end gap-4 sm:col-span-2">
        <CoverImage
          :aspect="release.data.value.cover_aspect"
          :src="release.data.value.cover_url"
          :title="release.data.value.title"
          :manufacturer="release.data.value.platform.manufacturer"
          class="w-24"
        />
        <p
          v-if="release.data.value.cover_from_game"
          class="text-xs text-muted-foreground"
          data-testid="cover-from-game"
        >
          {{ t('works.coverFromGame') }}
        </p>
        <input
          ref="fileInput"
          type="file"
          accept="image/jpeg,image/png,image/webp"
          class="hidden"
          :aria-label="t('items.uploadCover')"
          data-testid="cover-input"
          @change="upload"
        />
        <Button type="button" size="sm" variant="outline" @click="fileInput?.click()">
          <ImageUp class="size-4" /> {{ t('items.uploadCover') }}
        </Button>
        <Button
          v-if="auth.isAdmin"
          as-child
          type="button"
          size="sm"
          variant="ghost"
          data-testid="find-cover"
        >
          <RouterLink
            :to="{
              name: 'cover-search',
              params: { releaseId },
              query: { back: $route.fullPath },
            }"
          >
            <ImageIcon class="size-4" /> {{ t('integrations.covers.search') }}
          </RouterLink>
        </Button>
      </div>
    </EditSection>
    <EditSection :title="t('fields.barcodes')" :description="t('works.barcodeHint')">
      <p class="font-mono text-sm sm:col-span-2">
        {{ release.data.value.barcodes.join(', ') || '—' }}
      </p>
      <div class="grid gap-1.5">
        <Label for="r-barcode">{{ t('items.addBarcode') }}</Label>
        <Input
          id="r-barcode"
          v-model="barcode"
          autocapitalize="characters"
          spellcheck="false"
          class="font-mono"
          placeholder="4006381333931"
        />
      </div>
    </EditSection>
  </EditPage>
</template>
