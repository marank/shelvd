<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import { toast } from 'vue-sonner'
import EditPage from '@/components/app/EditPage.vue'
import EditSection from '@/components/app/EditSection.vue'
import PlatformBadge from '@/components/app/PlatformBadge.vue'
import ReleaseDate from '@/components/app/ReleaseDate.vue'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { useRelease } from '@/features/items/composables/useItem'
import { cn } from '@/lib/utils'
import WorkPicker from '../components/WorkPicker.vue'
import { backTarget } from '../composables/form'
import { useMoveRelease } from '../composables/useMerge'
import { workPage } from '../composables/target'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const releaseId = computed(() => String(route.params.releaseId))
const release = useRelease(releaseId)
const move = useMoveRelease()
const back = computed(() => backTarget(route.query.back))

const mode = ref<'existing' | 'own'>('existing')
const target = ref('')
const title = ref('')
watch(
  () => release.data.value,
  (value) => value && !title.value && (title.value = `${value.title} ${value.edition}`.trim()),
  { immediate: true },
)
const error = ref('')

async function submit() {
  error.value = ''
  if (mode.value === 'existing' && !target.value) {
    error.value = t('works.pickGame')
    return
  }
  try {
    const moved = await move.mutateAsync({
      releaseId: releaseId.value,
      workId: mode.value === 'existing' ? target.value : undefined,
      title: mode.value === 'own' ? title.value : '',
    })
    toast.success(t('works.releaseMoved'))
    void router.push(workPage(moved.work_id))
  } catch (e) {
    error.value = e instanceof Error ? e.message : t('errors.generic')
  }
}
</script>

<template>
  <EditPage
    v-if="release.data.value"
    :title="t('works.moveRelease')"
    :description="t('works.moveReleaseHint')"
    :back="back"
    :busy="move.isPending.value"
    :save-label="t('works.move')"
    :error="error"
    @submit="submit"
  >
    <EditSection :title="t('works.release')">
      <div class="flex flex-wrap items-center gap-2 sm:col-span-2" data-testid="moving-release">
        <span class="font-medium">{{ release.data.value.work_title }}</span>
        <PlatformBadge :platform="release.data.value.platform" />
        <span class="font-mono text-xs uppercase">{{ release.data.value.region }}</span>
        <span v-if="release.data.value.edition" class="text-sm">{{
          release.data.value.edition
        }}</span>
        <ReleaseDate :release="release.data.value" class="text-sm text-muted-foreground" />
      </div>
    </EditSection>
    <EditSection :title="t('works.whereTo')">
      <div class="grid gap-2 sm:col-span-2" role="radiogroup">
        <button
          v-for="option in ['existing', 'own'] as const"
          :key="option"
          type="button"
          role="radio"
          :aria-checked="mode === option"
          :data-testid="`mode-${option}`"
          :class="
            cn(
              'rounded-lg border p-3 text-left',
              mode === option ? 'border-primary bg-primary/5' : 'hover:bg-muted',
            )
          "
          @click="mode = option"
        >
          <span class="block text-sm font-medium">{{ t(`works.modes.${option}`) }}</span>
          <span class="block text-xs text-muted-foreground">{{
            t(`works.modes.${option}Hint`)
          }}</span>
        </button>
      </div>
      <div v-if="mode === 'existing'" class="sm:col-span-2">
        <WorkPicker v-model="target" :exclude="release.data.value.work_id" />
      </div>
      <div v-else class="grid gap-1.5 sm:col-span-2">
        <Label for="m-title">{{ t('works.newGameTitle') }}</Label>
        <Input id="m-title" v-model="title" />
      </div>
    </EditSection>
  </EditPage>
</template>
