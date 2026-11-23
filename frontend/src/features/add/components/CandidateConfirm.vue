<script setup lang="ts">
import RichText from '@/components/app/RichText.vue'
import { ArrowLeft, Download } from '@lucide/vue'
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import CoverImage from '@/components/app/CoverImage.vue'
import type { Candidate, Release } from '@/api/types'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Spinner } from '@/components/ui/spinner'
import { usePlatforms } from '@/features/library/composables/useReference'
import { isRegion, REGIONS, useImportCandidate, type Region } from '../composables/useAddApi'
import NativeSelect from '@/components/app/NativeSelect.vue'
import { firstText } from '@/lib/utils'

const props = defineProps<{
  candidate: Candidate
  barcode?: string | null
}>()
const emit = defineEmits<{ imported: [release: Release]; back: [] }>()
const { t } = useI18n()
const platforms = usePlatforms()
const importer = useImportCandidate()

const platformId = ref(props.candidate.platform_id ?? '')
const region = ref<Region>(isRegion(props.candidate.region) ? props.candidate.region : 'pal')
const manufacturer = computed(
  () => platforms.data.value?.find((p) => p.id === platformId.value)?.manufacturer,
)
const meta = computed(() =>
  [props.candidate.year, props.candidate.publisher].filter(Boolean).join(' · '),
)

function submit() {
  if (!platformId.value || importer.isPending.value) return
  importer.mutate(
    {
      provider: props.candidate.provider,
      external_id: props.candidate.external_id,
      platform_id: platformId.value,
      region: region.value,
      barcode: firstText(props.barcode) ?? null,
    },
    { onSuccess: (release) => emit('imported', release) },
  )
}
</script>

<template>
  <form class="grid grid-cols-1 gap-4" data-testid="candidate-confirm" @submit.prevent="submit">
    <div class="flex items-start gap-3">
      <CoverImage
        fit="box"
        :src="candidate.cover_url || null"
        :title="candidate.title"
        :manufacturer="manufacturer"
        class="w-16 shrink-0"
      />
      <div class="min-w-0 flex-1">
        <p class="font-medium break-words">{{ candidate.title }}</p>
        <p v-if="meta" class="text-sm text-muted-foreground">{{ meta }}</p>
        <p v-if="barcode" class="mt-1 font-mono text-xs text-muted-foreground tabular-nums">
          {{ barcode }}
        </p>
        <RichText
          v-if="candidate.summary"
          :text="candidate.summary"
          class="mt-2 line-clamp-3 text-xs text-muted-foreground"
        />
      </div>
    </div>

    <div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
      <div class="grid gap-1.5">
        <label for="import-platform" class="text-sm font-medium"
          >{{ t('fields.platform') }} *</label
        >
        <NativeSelect
          id="import-platform"
          v-model="platformId"
          required
          :aria-invalid="!platformId"
        >
          <option value="" disabled>{{ t('add.choose') }}</option>
          <option v-for="p in platforms.data.value ?? []" :key="p.id" :value="p.id">
            {{ p.name }}
          </option>
        </NativeSelect>
        <p v-if="!candidate.platform_id" class="text-xs text-muted-foreground">
          {{ t('add.confirm.platformUnknown', { name: candidate.platform_name || '—' }) }}
        </p>
      </div>
      <div class="grid gap-1.5">
        <label for="import-region" class="text-sm font-medium">{{ t('fields.region') }}</label>
        <NativeSelect id="import-region" v-model="region">
          <option v-for="r in REGIONS" :key="r" :value="r">{{ t(`choices.region.${r}`) }}</option>
        </NativeSelect>
      </div>
    </div>

    <Alert v-if="importer.error.value" variant="destructive" data-testid="import-error">
      <AlertDescription>{{ importer.error.value.message }}</AlertDescription>
    </Alert>

    <div class="flex flex-wrap justify-between gap-2">
      <Button type="button" variant="ghost" @click="emit('back')">
        <ArrowLeft class="size-4" />
        {{ t('actions.back') }}
      </Button>
      <Button
        type="submit"
        :disabled="!platformId || importer.isPending.value"
        data-testid="import"
      >
        <Spinner v-if="importer.isPending.value" />
        <Download v-else class="size-4" />
        {{ t('add.confirm.import') }}
      </Button>
    </div>
  </form>
</template>
