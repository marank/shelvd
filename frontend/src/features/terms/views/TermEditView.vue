<script setup lang="ts">
import { ImagePlus, Trash2, Upload, X } from '@lucide/vue'
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { toast } from 'vue-sonner'
import EditPage from '@/components/app/EditPage.vue'
import EditSection from '@/components/app/EditSection.vue'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import ConfirmDialog from '@/components/app/ConfirmDialog.vue'
import TermPicker from '@/features/works/components/TermPicker.vue'
import type { PickedTerm } from '@/features/works/composables/useTerms'
import { LOCALES } from '@/i18n'
import { countryName, languageName } from '@/lib/displayNames'
import { TERM_ICONS, termList, termPage } from '@/lib/terms'
import { termGames, useDescribers, useTerm, useTermMutations } from '../composables/useTermPages'
import { useTermRoute } from '../composables/useTermRoute'

/** A company's, genre's or series' name, description and picture (for everyone: it's the
 * catalog), a company's details, a series' franchise, or deleting it. The picture is saved right away, the
 * rest with Save. */
const { t, locale } = useI18n()
const router = useRouter()
const { kind, termId } = useTermRoute()
const term = useTerm(kind, termId)
const { update, remove, uploadImage, removeImage } = useTermMutations(kind)
const describers = useDescribers(kind)
const back = computed(() => termPage(kind.value, termId.value))

const form = ref<{ name: string; descriptions: Record<string, string> }>({
  name: '',
  descriptions: {},
})
/** One text per language, the reader's first. */
const languages = computed(() =>
  [...LOCALES].sort((a, b) => Number(b === locale.value) - Number(a === locale.value)),
)
interface CompanyForm {
  founded: string | number
  dissolved: string | number
  country: string
  headquarters: string
  website: string
  parent: PickedTerm[]
}

const company = ref<CompanyForm>({
  founded: '',
  dissolved: '',
  country: '',
  headquarters: '',
  website: '',
  parent: [],
})
const isCompany = computed(() => kind.value === 'companies')
const isSeries = computed(() => kind.value === 'series')
/** A series' franchise (an existing one). */
const franchise = ref<PickedTerm[]>([])
const loaded = ref(false)
watch(
  () => term.data.value,
  (value) => {
    if (!value || loaded.value) return
    loaded.value = true
    form.value = {
      name: value.name,
      descriptions: Object.fromEntries(LOCALES.map((l) => [l, value.descriptions[l] ?? ''])),
    }
    franchise.value = value.franchise ? [value.franchise] : []
    const details = value.company
    if (details)
      company.value = {
        founded: details.founded ?? '',
        dissolved: details.dissolved ?? '',
        country: details.country,
        headquarters: details.headquarters,
        website: details.website,
        parent: details.parent ? [details.parent] : [],
      }
  },
  { immediate: true },
)
const year = (value: string | number) => (value === '' ? null : Number(value))
const country = computed(() =>
  company.value.country.trim().length === 2
    ? countryName(company.value.country.trim(), locale.value)
    : '',
)
const error = ref('')
async function save() {
  error.value = ''
  const c = company.value
  try {
    await update.mutateAsync({
      termId: termId.value,
      ...form.value,
      ...(isCompany.value && {
        company: {
          founded: year(c.founded),
          dissolved: year(c.dissolved),
          country: c.country,
          headquarters: c.headquarters,
          website: c.website,
          parent: c.parent[0] ?? null,
        },
      }),
      ...(isSeries.value && {
        series: { franchise: franchise.value[0]?.id ? { id: franchise.value[0].id } : null },
      }),
    })
    toast.success(t('items.saved'))
    void router.push(back.value)
  } catch (e) {
    error.value = e instanceof Error ? e.message : t('errors.generic')
  }
}

const fileInput = ref<HTMLInputElement | null>(null)
async function onFile(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file) return
  try {
    await uploadImage.mutateAsync({ termId: termId.value, file })
    toast.success(t('terms.imageSaved'))
  } catch (e) {
    toast.error(e instanceof Error ? e.message : t('errors.generic'))
  }
}
async function dropImage() {
  try {
    await removeImage.mutateAsync(termId.value)
  } catch (e) {
    toast.error(e instanceof Error ? e.message : t('errors.generic'))
  }
}

const deleteOpen = ref(false)
const deleteError = ref('')
async function confirmDelete() {
  deleteError.value = ''
  try {
    await remove.mutateAsync(termId.value)
    toast.success(t('terms.deleted', { name: term.data.value?.name }))
    deleteOpen.value = false
    void router.push(termList(kind.value))
  } catch (e) {
    deleteError.value = e instanceof Error ? e.message : t('errors.generic')
  }
}
/** Games that lose the entry. */
const uses = computed(() => termGames(term.data.value).length)
</script>

<template>
  <EditPage
    v-if="term.data.value"
    :title="t(`terms.${kind}.edit`)"
    :description="t('terms.catalogHint')"
    :back="back"
    :busy="update.isPending.value"
    :error="error"
    @submit="save"
  >
    <template #actions>
      <Button
        type="button"
        variant="ghost"
        class="mr-auto text-destructive"
        data-testid="term-delete"
        @click="((deleteError = ''), (deleteOpen = true))"
      >
        <Trash2 class="size-4" /> {{ t('actions.delete') }}
      </Button>
    </template>
    <EditSection :title="t('terms.about')" :description="t('terms.nameHint')">
      <div class="grid gap-1.5 sm:col-span-2">
        <Label for="term-name">{{ t('terms.name') }}</Label>
        <Input id="term-name" v-model="form.name" required autocomplete="off" />
      </div>
      <div v-for="code in languages" :key="code" class="grid gap-1.5 sm:col-span-2">
        <Label :for="`term-description-${code}`">
          {{ t('terms.descriptionIn', { language: languageName(code, locale) }) }}
        </Label>
        <Textarea
          :id="`term-description-${code}`"
          v-model="form.descriptions[code]"
          rows="6"
          :placeholder="t(`terms.${kind}.descriptionHint`)"
        />
      </div>
    </EditSection>
    <EditSection
      v-if="isCompany"
      :title="t('terms.details.title')"
      :description="t('terms.details.hint')"
    >
      <div class="grid gap-1.5">
        <Label for="company-founded">{{ t('terms.details.founded') }}</Label>
        <Input
          id="company-founded"
          v-model="company.founded"
          type="number"
          min="1000"
          max="9999"
          inputmode="numeric"
        />
      </div>
      <div class="grid gap-1.5">
        <Label for="company-dissolved">{{ t('terms.details.dissolved') }}</Label>
        <Input
          id="company-dissolved"
          v-model="company.dissolved"
          type="number"
          min="1000"
          max="9999"
          inputmode="numeric"
        />
      </div>
      <div class="grid gap-1.5">
        <Label for="company-country">{{ t('terms.details.country') }}</Label>
        <Input
          id="company-country"
          v-model="company.country"
          maxlength="2"
          autocomplete="off"
          class="uppercase"
          :placeholder="t('terms.details.countryPlaceholder')"
          aria-describedby="company-country-name"
        />
        <p id="company-country-name" class="min-h-4 text-xs text-muted-foreground">
          {{ country }}
        </p>
      </div>
      <div class="grid gap-1.5">
        <Label for="company-headquarters">{{ t('terms.details.headquarters') }}</Label>
        <Input id="company-headquarters" v-model="company.headquarters" autocomplete="off" />
      </div>
      <div class="grid gap-1.5 sm:col-span-2">
        <Label for="company-website">{{ t('terms.details.website') }}</Label>
        <Input id="company-website" v-model="company.website" type="url" autocomplete="off" />
      </div>
      <div class="grid gap-1.5 sm:col-span-2">
        <Label for="company-parent">{{ t('terms.details.parent') }}</Label>
        <TermPicker
          id="company-parent"
          v-model="company.parent"
          kind="companies"
          existing-only
          :exclude="[termId]"
        />
      </div>
    </EditSection>
    <EditSection
      v-if="isSeries"
      :title="t('terms.franchiseOf')"
      :description="t('terms.franchiseOfHint')"
    >
      <div class="grid gap-1.5 sm:col-span-2">
        <Label for="series-franchise">{{ t('terms.franchises.one') }}</Label>
        <TermPicker
          id="series-franchise"
          v-model="franchise"
          kind="franchises"
          existing-only
          data-testid="series-franchise"
        />
      </div>
    </EditSection>
    <EditSection :title="t('terms.image')" :description="t('terms.imageHint')">
      <div class="flex flex-wrap items-center gap-3 sm:col-span-2">
        <div
          class="grid grid-cols-1 grid-rows-1 size-24 shrink-0 place-items-center rounded-xl border bg-card p-3"
          data-testid="term-image-preview"
        >
          <img
            v-if="term.data.value.image_url"
            :src="term.data.value.image_url"
            alt=""
            class="max-h-full max-w-full object-contain"
          />
          <component :is="TERM_ICONS[kind]" v-else class="size-8 text-muted-foreground/60" />
        </div>
        <input
          ref="fileInput"
          type="file"
          accept=".svg,image/svg+xml,image/png,image/webp,image/jpeg"
          class="sr-only"
          :aria-label="t('terms.upload')"
          data-testid="term-image-file"
          @change="onFile"
        />
        <Button
          type="button"
          variant="outline"
          size="sm"
          :disabled="uploadImage.isPending.value"
          @click="fileInput?.click()"
        >
          <Upload class="size-4" /> {{ t('terms.upload') }}
        </Button>
        <Button v-if="describers.length" variant="outline" size="sm" as-child>
          <RouterLink
            :to="{ name: `${kind}-image`, params: { termId } }"
            data-testid="term-image-choose"
          >
            <ImagePlus class="size-4" /> {{ t('terms.images.choose') }}
          </RouterLink>
        </Button>
        <Button
          v-if="term.data.value.image_url"
          type="button"
          variant="ghost"
          size="sm"
          data-testid="term-image-remove"
          @click="dropImage"
        >
          <X class="size-4" /> {{ t('terms.removeImage') }}
        </Button>
      </div>
    </EditSection>
  </EditPage>
  <ConfirmDialog
    v-model:open="deleteOpen"
    :title="t('terms.deleteTitle', { name: term.data.value?.name })"
    :description="t('terms.deleteText', { n: uses }, uses)"
    :confirm-label="t('actions.delete')"
    :busy="remove.isPending.value"
    :error="deleteError"
    @confirm="confirmDelete"
  />
</template>
