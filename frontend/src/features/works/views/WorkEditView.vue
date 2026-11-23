<script setup lang="ts">
import ForbiddenView from '@/features/library/views/ForbiddenView.vue'
import { ImageUp, Trash2 } from '@lucide/vue'
import { computed, reactive, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import { toast } from 'vue-sonner'
import EditPage from '@/components/app/EditPage.vue'
import CoverImage from '@/components/app/CoverImage.vue'
import EditSection from '@/components/app/EditSection.vue'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import TermPicker from '../components/TermPicker.vue'
import { backTarget } from '../composables/form'
import { termRefs, type PickedTerm } from '../composables/useTerms'
import { useUpdateWork, useWork, useWorkCover } from '../composables/useWork'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const workId = computed(() => String(route.params.workId))
const work = useWork(workId)
const update = useUpdateWork(workId)
const cover = useWorkCover(workId)
const fileInput = ref<HTMLInputElement | null>(null)
const back = computed(() => backTarget(route.query.back))

const form = reactive({
  title: '',
  series: [] as PickedTerm[],
  franchises: [] as PickedTerm[],
  summary: '',
  first_release_date: '',
  genres: [] as PickedTerm[],
  developers: [] as PickedTerm[],
})
const loaded = ref(false)
watch(
  () => work.data.value,
  (value) => {
    if (!value || loaded.value) return
    loaded.value = true
    Object.assign(form, {
      title: value.title,
      series: [...value.series],
      franchises: [...value.franchises],
      summary: value.summary,
      first_release_date: value.first_release_date ?? '',
      genres: [...value.genres],
      developers: [...value.developers],
    })
  },
  { immediate: true },
)
const error = ref('')

async function save() {
  error.value = ''
  try {
    await update.mutateAsync({
      title: form.title,
      series: termRefs(form.series),
      franchises: termRefs(form.franchises),
      summary: form.summary,
      first_release_date: form.first_release_date || null,
      genres: termRefs(form.genres),
      developers: termRefs(form.developers),
    })
    toast.success(t('items.saved'))
    void router.push(back.value)
  } catch (e) {
    error.value = e instanceof Error ? e.message : t('errors.generic')
  }
}

/** The cover is stored right away (like a release's), not with the form. */
async function uploadCover(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  error.value = ''
  try {
    await cover.upload.mutateAsync(file)
    toast.success(t('items.coverUploaded'))
  } catch (e) {
    error.value = e instanceof Error ? e.message : t('errors.generic')
  } finally {
    input.value = ''
  }
}
async function removeCover() {
  await cover.remove.mutateAsync()
  toast.success(t('works.coverRemoved'))
}
</script>

<template>
  <ForbiddenView v-if="work.data.value && !work.data.value.can_edit" />
  <EditPage
    v-else-if="work.data.value"
    :title="t('works.editGame')"
    :description="t('works.catalogHint')"
    :back="back"
    :busy="update.isPending.value"
    :error="error"
    @submit="save"
  >
    <EditSection :title="t('works.theGame')">
      <div class="grid gap-1.5 sm:col-span-2">
        <Label for="w-title">{{ t('fields.title') }}</Label>
        <Input id="w-title" v-model="form.title" required />
      </div>
      <div class="grid gap-1.5">
        <Label for="w-franchises">{{ t('fields.franchises') }}</Label>
        <TermPicker
          id="w-franchises"
          v-model="form.franchises"
          kind="franchises"
          multiple
          placeholder="Mario"
        />
      </div>
      <div class="grid gap-1.5">
        <Label for="w-series">{{ t('fields.series') }}</Label>
        <TermPicker
          id="w-series"
          v-model="form.series"
          kind="series"
          multiple
          placeholder="The Legend of Zelda"
        />
      </div>
      <div class="grid gap-1.5">
        <Label for="w-first">{{ t('works.firstRelease') }}</Label>
        <Input id="w-first" v-model="form.first_release_date" type="date" />
      </div>
      <div class="grid gap-1.5 sm:col-span-2">
        <Label for="w-summary">{{ t('fields.summary') }}</Label>
        <Textarea id="w-summary" v-model="form.summary" rows="6" />
      </div>
    </EditSection>
    <EditSection :title="t('fields.cover')" :description="t('works.gameCoverHint')">
      <div class="flex items-end gap-4 sm:col-span-2" data-testid="work-cover">
        <CoverImage
          v-if="work.data.value.has_cover"
          :src="work.data.value.cover_url"
          :aspect="work.data.value.cover_aspect"
          :title="work.data.value.title"
          class="w-32"
        />
        <p v-else class="text-sm text-muted-foreground">{{ t('works.noGameCover') }}</p>
        <input
          ref="fileInput"
          type="file"
          accept="image/jpeg,image/png,image/webp"
          class="hidden"
          :aria-label="t('items.uploadCover')"
          data-testid="work-cover-input"
          @change="uploadCover"
        />
        <Button type="button" size="sm" variant="outline" @click="fileInput?.click()">
          <ImageUp class="size-4" /> {{ t('items.uploadCover') }}
        </Button>
        <Button
          v-if="work.data.value.has_cover"
          type="button"
          size="sm"
          variant="ghost"
          data-testid="work-cover-remove"
          @click="removeCover"
        >
          <Trash2 class="size-4" /> {{ t('works.removeCover') }}
        </Button>
      </div>
    </EditSection>
    <EditSection :title="t('works.classification')">
      <div class="grid gap-1.5">
        <Label for="w-developers">{{ t('fields.developers') }}</Label>
        <TermPicker id="w-developers" v-model="form.developers" kind="companies" multiple />
      </div>
      <div class="grid gap-1.5">
        <Label for="w-genres">{{ t('fields.genres') }}</Label>
        <TermPicker id="w-genres" v-model="form.genres" kind="genres" multiple />
      </div>
    </EditSection>
  </EditPage>
</template>
