<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { Input } from '@/components/ui/input'
import type { Release } from '@/api/types'
import { PRECISIONS, type Precision } from '@/lib/releaseDate'
import { cn } from '@/lib/utils'

/**
 * A release date with precision: pick "exact day", "month", "quarter", … then enter just
 * what that precision needs. Emits the first day of the period as release_date.
 */
const model = defineModel<{
  release_precision: Release['release_precision']
  release_date: string | null
  release_date_end: string | null
}>({ required: true })
const { t } = useI18n()

const year = computed(
  () => Number(model.value.release_date?.slice(0, 4)) || new Date().getFullYear(),
)
const month = computed(() => Number(model.value.release_date?.slice(5, 7)) || 1)

function iso(y: number, m: number, d = 1): string {
  return `${String(y).padStart(4, '0')}-${String(m).padStart(2, '0')}-${String(d).padStart(2, '0')}`
}

function set(patch: Partial<typeof model.value>) {
  model.value = { ...model.value, ...patch }
}

function setPrecision(precision: Precision) {
  const date =
    precision === 'tba' ? null : (model.value.release_date ?? iso(year.value, month.value))
  set({ release_precision: precision, release_date: date, release_date_end: null })
}

const years = computed(() => {
  const now = new Date().getFullYear()
  return Array.from({ length: now + 6 - 1970 }, (_, i) => now + 5 - i)
})
const selectClass =
  'h-8 rounded-lg border border-input bg-transparent px-2 text-sm dark:bg-input/30 focus-visible:ring-3 focus-visible:ring-ring/50 outline-none'
</script>

<template>
  <div class="grid gap-2" data-testid="date-precision-input">
    <div class="flex flex-wrap gap-1" role="radiogroup" :aria-label="t('dates.precision')">
      <button
        v-for="p in PRECISIONS"
        :key="p"
        type="button"
        role="radio"
        :aria-checked="model.release_precision === p"
        :data-testid="`precision-${p}`"
        :class="
          cn(
            'h-7 rounded-md border px-2 text-xs',
            model.release_precision === p
              ? 'border-primary bg-primary text-primary-foreground'
              : 'bg-background text-muted-foreground hover:bg-muted hover:text-foreground',
          )
        "
        @click="setPrecision(p)"
      >
        {{ t(`dates.precisions.${p}`) }}
      </button>
    </div>
    <div class="flex flex-wrap items-center gap-2">
      <template v-if="['day', 'week', 'window'].includes(model.release_precision)">
        <Input
          type="date"
          class="w-auto"
          data-testid="date-start"
          :aria-label="t('dates.start')"
          :model-value="model.release_date ?? ''"
          @update:model-value="(v) => set({ release_date: String(v) || null })"
        />
        <template v-if="model.release_precision === 'window'">
          <span class="text-muted-foreground">–</span>
          <Input
            type="date"
            class="w-auto"
            data-testid="date-end"
            :aria-label="t('dates.end')"
            :model-value="model.release_date_end ?? ''"
            @update:model-value="(v) => set({ release_date_end: String(v) || null })"
          />
        </template>
      </template>
      <template v-else-if="model.release_precision !== 'tba'">
        <select
          v-if="model.release_precision === 'month'"
          :class="selectClass"
          data-testid="date-month"
          :aria-label="t('dates.month')"
          :value="month"
          @change="
            (e) => set({ release_date: iso(year, Number((e.target as HTMLSelectElement).value)) })
          "
        >
          <option v-for="m in 12" :key="m" :value="m">
            {{
              new Intl.DateTimeFormat($i18n.locale, { month: 'long' }).format(
                new Date(2000, m - 1, 1),
              )
            }}
          </option>
        </select>
        <select
          v-if="model.release_precision === 'quarter'"
          :class="selectClass"
          data-testid="date-quarter"
          :aria-label="t('dates.precisions.quarter')"
          :value="Math.floor((month - 1) / 3)"
          @change="
            (e) =>
              set({
                release_date: iso(year, Number((e.target as HTMLSelectElement).value) * 3 + 1),
              })
          "
        >
          <option v-for="q in 4" :key="q" :value="q - 1">Q{{ q }}</option>
        </select>
        <select
          v-if="model.release_precision === 'half'"
          :class="selectClass"
          data-testid="date-half"
          :aria-label="t('dates.precisions.half')"
          :value="month <= 6 ? 1 : 7"
          @change="
            (e) => set({ release_date: iso(year, Number((e.target as HTMLSelectElement).value)) })
          "
        >
          <option :value="1">H1</option>
          <option :value="7">H2</option>
        </select>
        <select
          :class="selectClass"
          data-testid="date-year"
          :aria-label="t('fields.year')"
          :value="year"
          @change="
            (e) => set({ release_date: iso(Number((e.target as HTMLSelectElement).value), month) })
          "
        >
          <option v-for="y in years" :key="y" :value="y">{{ y }}</option>
        </select>
      </template>
      <span v-else class="text-sm text-muted-foreground italic">{{ t('dates.tbaHint') }}</span>
    </div>
  </div>
</template>
