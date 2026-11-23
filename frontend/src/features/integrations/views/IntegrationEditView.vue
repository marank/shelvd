<script setup lang="ts">
import { CircleAlert, CircleCheck, ExternalLink, FlaskConical } from '@lucide/vue'
import { computed, reactive, ref, watch, type Component } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import { toast } from 'vue-sonner'
import { collect } from '@/addons'
import EditPage from '@/components/app/EditPage.vue'
import EditSection from '@/components/app/EditSection.vue'
import NativeSelect from '@/components/app/NativeSelect.vue'
import type { Integration } from '@/api/types'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  useIntegrations,
  useSaveIntegration,
  useTestIntegration,
  type IntegrationChanges,
} from '../composables/useIntegrations'

/** One integration's settings: on/off, keys (write-only), freshness, background refresh. */
const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const key = computed(() => String(route.params.key))
const integrations = useIntegrations()
const save = useSaveIntegration()
const tester = useTestIntegration()
const integration = computed(() => integrations.data.value?.find((i) => i.key === key.value))
const back = { name: 'integrations' }

const FRESHNESS = ['max_age_hours', 'periodic', 'periodic_hours', 'batch']
type HourField = 'max_age_hours' | 'periodic_hours'
const isHourField = (name: string): name is HourField => name.endsWith('_hours')
interface IntegrationForm {
  enabled: boolean
  // eslint-disable-next-line @typescript-eslint/no-explicit-any -- text, number or switch
  options: Record<string, any>
  secrets: Record<string, string>
  removed: string[]
  /** Hour fields are edited as a number plus a unit. */
  units: Record<HourField, 'hours' | 'days'>
}

const form = reactive<IntegrationForm>({
  enabled: false,
  options: {},
  secrets: {},
  removed: [],
  units: { max_age_hours: 'hours', periodic_hours: 'hours' },
})
const loaded = ref(false)
watch(
  integration,
  (value) => {
    if (!value || loaded.value) return
    loaded.value = true
    form.enabled = value.enabled
    for (const f of value.fields.filter((f) => !f.secret)) {
      const raw = f.value as string | number | boolean | null
      if (isHourField(f.name) && typeof raw === 'number' && raw % 24 === 0) {
        form.units[f.name] = 'days'
        form.options[f.name] = raw / 24
      } else {
        form.options[f.name] = raw ?? (f.type === 'bool' ? false : '')
      }
    }
  },
  { immediate: true },
)
/** Fields set by a flow of their own, not typed in: add-ons bring the flow's section. */
const FLOW_SECTIONS = Object.assign({}, ...collect('integrationFlows')) as Record<string, Component>
const FLOWS = Object.keys(FLOW_SECTIONS)
const flows = computed(() =>
  Object.entries(FLOW_SECTIONS)
    .filter(([name]) => has(name))
    .map(([name, section]) => ({ name, section })),
)
const secretFields = computed(
  () => integration.value?.fields.filter((f) => f.secret && !FLOWS.includes(f.name)) ?? [],
)
const accessFields = computed(
  () => integration.value?.fields.filter((f) => !f.secret && !FRESHNESS.includes(f.name)) ?? [],
)
const freshness = computed(() => integration.value?.refreshes ?? false)
/** Play time integrations have only the periodic sync, not max age and batch size. */
const has = (name: string) => !!integration.value?.fields.some((f) => f.name === name)
const error = ref('')
const result = ref<{ ok: boolean; message: string } | null>(null)

function changes(): IntegrationChanges {
  const options = Object.fromEntries(
    Object.entries(form.options).map(([name, value]) => [
      name,
      isHourField(name) && form.units[name] === 'days' ? Number(value) * 24 : value,
    ]),
  )
  const secrets = Object.fromEntries([
    ...Object.entries(form.secrets).filter(([, value]) => value.trim()),
    ...form.removed.map((name) => [name, '']),
  ])
  return { enabled: form.enabled, options, secrets }
}

async function store(): Promise<Integration | null> {
  error.value = ''
  try {
    const saved = await save.mutateAsync({ key: key.value, body: changes() })
    form.secrets = {}
    form.removed = []
    return saved
  } catch (e) {
    error.value = (e as Error).message
    return null
  }
}

async function submit() {
  const saved = await store()
  if (!saved) return
  toast.success(t('integrations.edit.saved', { name: saved.name }))
  await router.push(back)
}

async function test() {
  result.value = null
  if (!(await store())) return
  result.value = await tester.mutateAsync(key.value)
}

const toggleRemoved = (name: string) =>
  (form.removed = form.removed.includes(name)
    ? form.removed.filter((n) => n !== name)
    : [...form.removed, name])
</script>

<template>
  <EditPage
    v-if="integration"
    :title="t('integrations.edit.title', { name: integration.name })"
    :description="t(`integrations.about.${integration.key}`)"
    :back="back"
    :busy="save.isPending.value || tester.isPending.value"
    :error="error"
    @submit="submit"
  >
    <template #actions>
      <Button
        type="button"
        variant="outline"
        class="mr-auto"
        data-testid="test-integration"
        :disabled="save.isPending.value || tester.isPending.value"
        @click="test"
      >
        <FlaskConical class="size-4" /> {{ t('integrations.edit.test') }}
      </Button>
    </template>

    <Alert v-if="integration.unofficial" class="mt-6" data-testid="unofficial">
      <CircleAlert class="size-4" />
      <AlertDescription>{{ t('integrations.unofficialText') }}</AlertDescription>
    </Alert>
    <Alert
      v-if="result"
      class="mt-6"
      :variant="result.ok ? 'default' : 'destructive'"
      data-testid="test-result"
    >
      <CircleCheck v-if="result.ok" class="size-4" />
      <CircleAlert v-else class="size-4" />
      <AlertDescription>
        {{
          t(result.ok ? 'integrations.edit.testOk' : 'integrations.edit.testFailed', {
            message: result.message,
          })
        }}
      </AlertDescription>
    </Alert>

    <EditSection
      :title="t('integrations.edit.enabled')"
      :description="t('integrations.edit.enabledText')"
    >
      <label class="flex items-center gap-2 text-sm sm:col-span-2">
        <Checkbox
          :model-value="form.enabled"
          @update:model-value="form.enabled = $event === true"
          data-testid="enabled"
        />
        {{ t('integrations.edit.enabled') }}
      </label>
    </EditSection>

    <EditSection
      v-if="secretFields.length || accessFields.length"
      :title="t('integrations.edit.access')"
      :description="t('integrations.edit.accessText')"
    >
      <template v-for="f in accessFields" :key="f.name">
        <label v-if="f.type === 'bool'" class="flex items-start gap-2 text-sm sm:col-span-2">
          <Checkbox
            v-model="form.options[f.name]"
            class="mt-0.5"
            :data-testid="`field-${f.name}`"
          />
          <span>
            {{ t(`integrations.fields.${f.name}`) }}
            <span class="block text-xs text-muted-foreground">
              {{ t(`integrations.fieldHelp.${f.name}`) }}
            </span>
          </span>
        </label>
        <div v-else class="grid gap-1.5 sm:col-span-2">
          <Label :for="`i-${f.name}`">{{ t(`integrations.fields.${f.name}`) }}</Label>
          <Input
            :id="`i-${f.name}`"
            v-model="form.options[f.name]"
            autocomplete="off"
            :data-testid="`field-${f.name}`"
          />
        </div>
      </template>
      <div v-for="f in secretFields" :key="f.name" class="grid gap-1.5 sm:col-span-2">
        <Label :for="`i-${f.name}`">{{ t(`integrations.fields.${f.name}`) }}</Label>
        <div class="flex items-center gap-2">
          <Input
            :id="`i-${f.name}`"
            v-model="form.secrets[f.name]"
            type="password"
            autocomplete="new-password"
            :placeholder="f.has_value ? f.masked : ''"
            :disabled="form.removed.includes(f.name)"
            :data-testid="`field-${f.name}`"
          />
          <Button
            v-if="f.has_value"
            type="button"
            variant="ghost"
            size="sm"
            :data-testid="`remove-${f.name}`"
            @click="toggleRemoved(f.name)"
          >
            {{ t('integrations.edit.remove') }}
          </Button>
        </div>
        <p class="text-xs text-muted-foreground">
          {{
            form.removed.includes(f.name)
              ? t('integrations.edit.removed')
              : f.has_value
                ? t('integrations.edit.secretSet', { masked: f.masked })
                : t('integrations.edit.secretMissing')
          }}
        </p>
      </div>
      <a
        :href="integration.url"
        target="_blank"
        rel="noopener"
        class="inline-flex w-fit items-center gap-1 text-sm text-primary underline-offset-4 hover:underline sm:col-span-2"
      >
        {{ t('integrations.docs') }} <ExternalLink class="size-3.5" />
      </a>
    </EditSection>

    <template v-if="integration">
      <component
        :is="flow.section"
        v-for="flow in flows"
        :key="flow.name"
        :integration="integration"
      />
    </template>

    <EditSection
      v-if="freshness"
      :title="t('integrations.edit.freshness')"
      :description="t('integrations.edit.freshnessText')"
    >
      <div v-if="has('max_age_hours')" class="grid gap-1.5 sm:col-span-2">
        <Label for="i-max_age_hours">{{ t('integrations.fields.max_age_hours') }}</Label>
        <div class="flex gap-2">
          <Input
            id="i-max_age_hours"
            v-model="form.options.max_age_hours"
            type="number"
            min="1"
            class="w-28"
            data-testid="field-max_age_hours"
          />
          <NativeSelect
            v-model="form.units.max_age_hours"
            class="w-32"
            data-testid="unit-max_age_hours"
          >
            <option value="hours">{{ t('integrations.edit.hours') }}</option>
            <option value="days">{{ t('integrations.edit.days') }}</option>
          </NativeSelect>
        </div>
      </div>
      <label class="flex items-start gap-2 text-sm sm:col-span-2">
        <Checkbox v-model="form.options.periodic" class="mt-0.5" data-testid="field-periodic" />
        <span>
          {{ t('integrations.fields.periodic') }}
          <span class="block text-xs text-muted-foreground">
            {{ t('integrations.edit.periodicText') }}
          </span>
        </span>
      </label>
      <template v-if="form.options.periodic">
        <div class="grid gap-1.5">
          <Label for="i-periodic_hours">{{ t('integrations.fields.periodic_hours') }}</Label>
          <div class="flex gap-2">
            <Input
              id="i-periodic_hours"
              v-model="form.options.periodic_hours"
              type="number"
              min="1"
              class="w-24"
              data-testid="field-periodic_hours"
            />
            <NativeSelect v-model="form.units.periodic_hours" class="w-28">
              <option value="hours">{{ t('integrations.edit.hours') }}</option>
              <option value="days">{{ t('integrations.edit.days') }}</option>
            </NativeSelect>
          </div>
        </div>
        <div v-if="has('batch')" class="grid gap-1.5">
          <Label for="i-batch">{{ t('integrations.fields.batch') }}</Label>
          <Input
            id="i-batch"
            v-model="form.options.batch"
            type="number"
            min="1"
            class="w-24"
            data-testid="field-batch"
          />
        </div>
      </template>
    </EditSection>
  </EditPage>
  <p
    v-else-if="integrations.isError.value"
    class="p-6 text-sm text-muted-foreground"
    data-testid="not-allowed"
  >
    {{ integrations.error.value?.message }}
  </p>
</template>
