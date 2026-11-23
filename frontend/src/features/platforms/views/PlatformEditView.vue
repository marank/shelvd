<script setup lang="ts">
import { Circle, ImagePlus, Trash2, Upload, X } from '@lucide/vue'
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import { toast } from 'vue-sonner'
import EditPage from '@/components/app/EditPage.vue'
import EditSection from '@/components/app/EditSection.vue'
import NativeSelect from '@/components/app/NativeSelect.vue'
import PlatformBadge from '@/components/app/PlatformBadge.vue'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Skeleton } from '@/components/ui/skeleton'
import { useDescribers } from '@/features/terms/composables/useTermPages'
import { backTarget } from '@/features/works/composables/form'
import { LOCALES } from '@/i18n'
import { languageName } from '@/lib/displayNames'
import { brandColor } from '@/lib/labels'
import { imageRoute } from '@/lib/terms'
import { PLATFORM_ICONS } from '@/lib/platformIcons'
import { cn } from '@/lib/utils'
import ConfirmDialog from '@/components/app/ConfirmDialog.vue'
import {
  usePlatform,
  usePlatformMutations,
  type PictureSlot,
  type PlatformIn,
} from '../composables/usePlatforms'
import { usePlatforms } from '@/features/library/composables/useReference'

/** Create (platform-new) or edit (platform-edit) a platform: names, colour and icon, its
 * page's picture, descriptions and facts. Pictures are saved right away, the rest with
 * Save. */
const { t, locale } = useI18n()
const route = useRoute()
const router = useRouter()
const platformId = computed(() => String(route.params.platformId ?? ''))
const isNew = computed(() => !platformId.value)
const platform = usePlatform(platformId)
const { create, update, remove, uploadIcon, removeIcon, uploadPicture, removePicture } =
  usePlatformMutations()
const back = computed(() =>
  typeof route.query.back === 'string' ? backTarget(route.query.back) : { name: 'platforms' },
)
const describers = useDescribers('platforms')
const allPlatforms = usePlatforms()
/** Other platforms, by maker and year, to pick predecessors from. */
const others = computed(() =>
  (allPlatforms.data.value ?? []).filter((p) => p.id !== platformId.value),
)
/** The reader's language first. */
const languages = computed(() => [locale.value, ...LOCALES.filter((l) => l !== locale.value)])
const MEDIA_TYPES = ['game', 'toy', 'video'] as const
type MediaType = (typeof MEDIA_TYPES)[number]

interface PlatformForm {
  name: string
  short_name: string
  manufacturer: string
  media_type: MediaType
  release_year: string
  color: string
  icon: string
  igdb_id: string
  descriptions: Record<string, string>
  generation: string
  discontinued: string
  predecessors: string[]
}

const form = ref<PlatformForm>({
  name: '',
  short_name: '',
  manufacturer: '',
  media_type: 'game',
  release_year: '',
  color: '',
  icon: '',
  igdb_id: '',
  descriptions: {},
  generation: '',
  discontinued: '',
  predecessors: [],
})
watch(
  () => platform.data.value,
  (p, previous) => {
    if (!p || previous?.id === p.id) return
    form.value = {
      name: p.name,
      short_name: p.short_name,
      manufacturer: p.manufacturer,
      media_type: p.media_type as MediaType,
      release_year: p.release_year ? String(p.release_year) : '',
      color: p.color,
      icon: p.icon,
      igdb_id: p.igdb_id === null ? '' : String(p.igdb_id),
      descriptions: Object.fromEntries(LOCALES.map((l) => [l, p.descriptions[l] ?? ''])),
      generation: p.generation ? String(p.generation) : '',
      discontinued: p.discontinued ? String(p.discontinued) : '',
      predecessors: p.predecessors.map((o) => o.id),
    }
  },
  { immediate: true },
)
/** The badge as it will look, before saving. */
const preview = computed(() => ({
  name: form.value.name || t('platforms.edit.name'),
  short_name: form.value.short_name,
  manufacturer: form.value.manufacturer,
  color: form.value.color,
  icon: form.value.icon,
  icon_url: platform.data.value?.icon_url ?? null,
}))
const pickerColor = computed(() => form.value.color || '#888888')
const usesBrand = computed(() => !brandColor(form.value.manufacturer).includes('other'))

const error = ref('')
const busy = computed(() => create.isPending.value || update.isPending.value)
const toNumber = (v: string) => (v.trim() ? Number(v) : null)

async function save() {
  const body: PlatformIn = {
    ...form.value,
    name: form.value.name.trim(),
    release_year: toNumber(form.value.release_year),
    igdb_id: toNumber(form.value.igdb_id),
    generation: toNumber(form.value.generation),
    discontinued: toNumber(form.value.discontinued),
  }
  if (!body.name) {
    error.value = t('platforms.edit.nameRequired')
    return
  }
  error.value = ''
  try {
    if (isNew.value) {
      const created = await create.mutateAsync(body)
      toast.success(t('platforms.edit.saved', { name: body.name }))
      // Icons need the platform's id: stay on its page for the upload.
      await router.push({ name: 'platform-edit', params: { platformId: created.id } })
    } else {
      await update.mutateAsync({ id: platformId.value, body })
      toast.success(t('platforms.edit.saved', { name: body.name }))
      await router.push(back.value)
    }
  } catch (e) {
    error.value = (e as Error).message
  }
}

function togglePredecessor(id: string) {
  const list = form.value.predecessors
  form.value.predecessors = list.includes(id) ? list.filter((x) => x !== id) : [...list, id]
}

/** The page's two pictures: the logo and a photo of the device. */
const SLOTS: PictureSlot[] = ['image', 'photo']
const pictureUrl = (slot: PictureSlot) =>
  slot === 'image' ? platform.data.value?.image_url : platform.data.value?.photo_url
const pictureInputs = ref<Partial<Record<PictureSlot, HTMLInputElement | null>>>({})
async function onPicture(slot: PictureSlot, event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file) return
  try {
    await uploadPicture.mutateAsync({ id: platformId.value, slot, file })
    toast.success(t(`platforms.edit.saved_${slot}`))
  } catch (e) {
    toast.error((e as Error).message)
  }
}
async function dropPicture(slot: PictureSlot) {
  try {
    await removePicture.mutateAsync({ id: platformId.value, slot })
  } catch (e) {
    toast.error((e as Error).message)
  }
}

const fileInput = ref<HTMLInputElement | null>(null)
async function onFile(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file) return
  try {
    await uploadIcon.mutateAsync({ id: platformId.value, file })
    toast.success(t('platforms.edit.iconUploaded'))
  } catch (e) {
    toast.error((e as Error).message)
  }
}
async function dropIcon() {
  try {
    await removeIcon.mutateAsync(platformId.value)
  } catch (e) {
    toast.error((e as Error).message)
  }
}

const deleteOpen = ref(false)
const deleteError = ref('')
async function confirmDelete() {
  try {
    await remove.mutateAsync(platformId.value)
    toast.success(t('platforms.edit.deleted', { name: form.value.name }))
    deleteOpen.value = false
    await router.push({ name: 'platforms' })
  } catch (e) {
    deleteError.value = (e as Error).message
  }
}
</script>

<template>
  <EditPage
    :title="isNew ? t('platforms.edit.newTitle') : form.name || t('platforms.edit.title')"
    :description="t('platforms.edit.description')"
    :back="back"
    :busy="busy"
    :error="error"
    @submit="save"
  >
    <template v-if="!isNew && platform.data.value" #actions>
      <Button
        type="button"
        variant="ghost"
        class="mr-auto text-destructive"
        :disabled="platform.data.value.release_count > 0"
        :title="
          platform.data.value.release_count
            ? t('platforms.edit.inUse', platform.data.value.release_count)
            : undefined
        "
        data-testid="platform-delete"
        @click="((deleteError = ''), (deleteOpen = true))"
      >
        <Trash2 class="size-4" /> {{ t('actions.delete') }}
      </Button>
    </template>

    <div v-if="!isNew && platform.isPending.value" class="py-6">
      <Skeleton class="h-40 rounded-lg" />
    </div>
    <Alert v-else-if="!isNew && platform.isError.value" variant="destructive" class="my-6">
      <AlertDescription>{{ platform.error.value?.message }}</AlertDescription>
    </Alert>
    <template v-else>
      <EditSection :title="t('platforms.edit.general')">
        <div class="grid gap-1.5 sm:col-span-2">
          <Label for="platform-name">{{ t('platforms.edit.name') }}</Label>
          <Input
            id="platform-name"
            v-model="form.name"
            placeholder="Nintendo Switch 2"
            data-testid="platform-name"
          />
        </div>
        <div class="grid gap-1.5">
          <Label for="platform-short">{{ t('platforms.edit.shortName') }}</Label>
          <Input id="platform-short" v-model="form.short_name" placeholder="Switch 2" />
        </div>
        <div class="grid gap-1.5">
          <Label for="platform-maker">{{ t('platforms.edit.manufacturer') }}</Label>
          <Input
            id="platform-maker"
            v-model="form.manufacturer"
            placeholder="Nintendo"
            data-testid="platform-manufacturer"
          />
        </div>
        <div class="grid gap-1.5">
          <Label for="platform-media">{{ t('platforms.edit.mediaType') }}</Label>
          <NativeSelect id="platform-media" v-model="form.media_type">
            <option v-for="m in MEDIA_TYPES" :key="m" :value="m">
              {{ t(`choices.media_type.${m}`) }}
            </option>
          </NativeSelect>
        </div>
        <div class="grid gap-1.5">
          <Label for="platform-year">{{ t('platforms.edit.year') }}</Label>
          <Input
            id="platform-year"
            v-model="form.release_year"
            inputmode="numeric"
            class="tabular font-mono"
            placeholder="2025"
          />
        </div>
        <div class="grid gap-1.5">
          <Label for="platform-discontinued">{{ t('platforms.edit.discontinued') }}</Label>
          <Input
            id="platform-discontinued"
            v-model="form.discontinued"
            inputmode="numeric"
            class="tabular font-mono"
            placeholder="2025"
          />
        </div>
        <div class="grid gap-1.5">
          <Label for="platform-generation">{{ t('platforms.edit.generation') }}</Label>
          <Input
            id="platform-generation"
            v-model="form.generation"
            inputmode="numeric"
            class="tabular font-mono"
            placeholder="8"
          />
        </div>
      </EditSection>

      <EditSection :title="t('platforms.edit.about')" :description="t('platforms.edit.aboutText')">
        <div v-for="code in languages" :key="code" class="grid gap-1.5 sm:col-span-2">
          <Label :for="`platform-description-${code}`">
            {{ t('terms.descriptionIn', { language: languageName(code, locale) }) }}
          </Label>
          <Textarea
            :id="`platform-description-${code}`"
            v-model="form.descriptions[code]"
            rows="5"
          />
        </div>
        <div class="grid gap-1.5 sm:col-span-2">
          <span class="text-sm font-medium">{{ t('platforms.edit.predecessors') }}</span>
          <div class="flex flex-wrap gap-1.5" data-testid="platform-predecessors">
            <button
              v-for="p in others"
              :key="p.id"
              type="button"
              :aria-pressed="form.predecessors.includes(p.id)"
              :class="
                cn(
                  'rounded-md border px-2 py-1 text-xs text-muted-foreground transition-colors hover:bg-muted/50',
                  form.predecessors.includes(p.id) && 'border-primary bg-primary/5 text-foreground',
                )
              "
              :data-testid="`predecessor-${p.id}`"
              @click="togglePredecessor(p.id)"
            >
              {{ p.short_name || p.name }}
            </button>
          </div>
        </div>
      </EditSection>

      <EditSection
        v-if="!isNew"
        :title="t('platforms.edit.picture')"
        :description="t('platforms.edit.pictureText')"
      >
        <div v-for="slot in SLOTS" :key="slot" class="grid gap-1.5 sm:col-span-2">
          <span class="text-sm font-medium">{{ t(`platforms.edit.slot_${slot}`) }}</span>
          <div class="flex flex-wrap items-center gap-3">
            <div
              class="grid grid-cols-1 grid-rows-1 size-24 shrink-0 place-items-center rounded-xl border bg-card p-2"
              :data-testid="`platform-${slot}`"
            >
              <img
                v-if="pictureUrl(slot)"
                :src="pictureUrl(slot)!"
                alt=""
                class="max-h-full max-w-full object-contain"
              />
            </div>
            <input
              :ref="(el) => (pictureInputs[slot] = el as HTMLInputElement | null)"
              type="file"
              accept=".svg,image/svg+xml,image/png,image/webp,image/jpeg"
              class="sr-only"
              :aria-label="t('platforms.edit.upload')"
              :data-testid="`platform-${slot}-file`"
              @change="onPicture(slot, $event)"
            />
            <Button
              type="button"
              variant="outline"
              size="sm"
              :disabled="uploadPicture.isPending.value"
              @click="pictureInputs[slot]?.click()"
            >
              <Upload class="size-4" /> {{ t('platforms.edit.upload') }}
            </Button>
            <Button v-if="describers.length" variant="outline" size="sm" as-child>
              <RouterLink
                :to="imageRoute('platforms', platformId)"
                :data-testid="`platform-${slot}-choose`"
              >
                <ImagePlus class="size-4" /> {{ t('terms.images.choose') }}
              </RouterLink>
            </Button>
            <Button
              v-if="pictureUrl(slot)"
              type="button"
              variant="ghost"
              size="sm"
              :data-testid="`platform-${slot}-remove`"
              @click="dropPicture(slot)"
            >
              <X class="size-4" /> {{ t('platforms.edit.removePicture') }}
            </Button>
          </div>
        </div>
      </EditSection>

      <EditSection :title="t('platforms.edit.look')" :description="t('platforms.edit.lookText')">
        <div class="flex items-center gap-3 sm:col-span-2" data-testid="platform-preview">
          <span class="font-mono text-[11px] tracking-wider text-muted-foreground uppercase">
            {{ t('platforms.edit.preview') }}
          </span>
          <PlatformBadge :platform="preview" />
        </div>

        <div class="grid gap-1.5 sm:col-span-2">
          <Label for="platform-color">{{ t('platforms.edit.color') }}</Label>
          <div class="flex flex-wrap items-center gap-2">
            <input
              id="platform-color"
              type="color"
              :value="pickerColor"
              class="h-9 w-12 cursor-pointer rounded-md border bg-transparent p-1"
              data-testid="platform-color"
              @input="form.color = ($event.target as HTMLInputElement).value"
            />
            <Input
              v-model="form.color"
              class="tabular w-32 font-mono"
              placeholder="#e60012"
              :aria-label="t('platforms.edit.color')"
            />
            <Button
              v-if="form.color"
              type="button"
              variant="ghost"
              size="sm"
              data-testid="platform-color-reset"
              @click="form.color = ''"
            >
              <X class="size-4" />
              {{ usesBrand ? t('platforms.edit.brandColor') : t('platforms.edit.noColor') }}
            </Button>
          </div>
        </div>

        <div class="grid gap-1.5 sm:col-span-2">
          <span class="text-sm font-medium">{{ t('platforms.edit.icon') }}</span>
          <div
            class="grid grid-cols-5 gap-1.5 sm:grid-cols-8"
            role="radiogroup"
            :aria-label="t('platforms.edit.icon')"
          >
            <button
              v-for="key in ['', ...Object.keys(PLATFORM_ICONS)]"
              :key="key || 'none'"
              type="button"
              role="radio"
              :aria-checked="form.icon === key"
              :title="t(`platforms.icons.${key || 'none'}`)"
              :class="
                cn(
                  'flex h-10 items-center justify-center rounded-md border transition-colors hover:bg-muted/50',
                  form.icon === key && 'border-primary bg-primary/5',
                )
              "
              :data-testid="`icon-${key || 'none'}`"
              @click="form.icon = key"
            >
              <component
                :is="key ? PLATFORM_ICONS[key] : Circle"
                class="size-4"
                :class="!key && 'size-2 fill-current'"
                :style="{ color: form.color || undefined }"
              />
              <span class="sr-only">{{ t(`platforms.icons.${key || 'none'}`) }}</span>
            </button>
          </div>
        </div>

        <div class="grid gap-1.5 sm:col-span-2">
          <span class="text-sm font-medium">{{ t('platforms.edit.ownIcon') }}</span>
          <p v-if="isNew" class="text-sm text-muted-foreground">
            {{ t('platforms.edit.ownIconLater') }}
          </p>
          <div v-else class="flex flex-wrap items-center gap-2">
            <img
              v-if="platform.data.value?.icon_url"
              :src="platform.data.value.icon_url"
              alt=""
              class="size-9 rounded-md border object-contain p-1"
              data-testid="platform-own-icon"
            />
            <input
              ref="fileInput"
              type="file"
              accept=".svg,image/svg+xml,image/png,image/webp,image/jpeg"
              class="sr-only"
              :aria-label="t('platforms.edit.upload')"
              data-testid="platform-icon-file"
              @change="onFile"
            />
            <Button
              type="button"
              variant="outline"
              size="sm"
              :disabled="uploadIcon.isPending.value"
              @click="fileInput?.click()"
            >
              <Upload class="size-4" /> {{ t('platforms.edit.upload') }}
            </Button>
            <Button
              v-if="platform.data.value?.icon_url"
              type="button"
              variant="ghost"
              size="sm"
              data-testid="platform-icon-remove"
              @click="dropIcon"
            >
              <X class="size-4" /> {{ t('platforms.edit.removeIcon') }}
            </Button>
            <p class="w-full text-xs text-muted-foreground">
              {{ t('platforms.edit.ownIconText') }}
            </p>
          </div>
        </div>
      </EditSection>

      <EditSection
        :title="t('platforms.edit.sources')"
        :description="t('platforms.edit.sourcesText')"
      >
        <div class="grid gap-1.5">
          <Label for="platform-igdb">IGDB-ID</Label>
          <Input
            id="platform-igdb"
            v-model="form.igdb_id"
            inputmode="numeric"
            class="tabular font-mono"
            placeholder="508"
          />
        </div>
      </EditSection>
    </template>
  </EditPage>
  <ConfirmDialog
    v-model:open="deleteOpen"
    :title="t('platforms.edit.deleteTitle')"
    :description="t('platforms.edit.deleteText', { name: form.name })"
    :confirm-label="t('actions.delete')"
    :busy="remove.isPending.value"
    :error="deleteError"
    @confirm="confirmDelete"
  />
</template>
