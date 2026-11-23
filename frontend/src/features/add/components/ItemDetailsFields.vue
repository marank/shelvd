<script setup lang="ts">
// The copy's own fields (format, status, place, owner, purchase …): the add dialog's
// "More details" and the scan round's defaults use the same form; price and notes
// (`perCopy`) only make sense for one copy.
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import NativeSelect from '@/components/app/NativeSelect.vue'
import ChoiceNativeSelect from '@/features/items/components/ChoiceNativeSelect.vue'
import { useLocations, usePeople } from '@/features/library/composables/useReference'
import { useI18n } from 'vue-i18n'
import type { ItemDetails } from '../composables/useItemDetails'

const props = defineProps<{ libraryId: string; perCopy?: boolean }>()
const details = defineModel<ItemDetails>('details', { required: true })
const { t } = useI18n()
const locations = useLocations(() => props.libraryId)
const people = usePeople(() => props.libraryId)
</script>

<template>
  <div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
    <div class="grid gap-1.5">
      <label for="item-format" class="text-sm font-medium">{{ t('fields.format') }}</label>
      <ChoiceNativeSelect id="item-format" v-model="details.format" field="format" />
    </div>
    <div class="grid gap-1.5">
      <label for="item-status" class="text-sm font-medium">{{ t('fields.status') }}</label>
      <ChoiceNativeSelect id="item-status" v-model="details.status" field="status" />
    </div>
    <div class="grid gap-1.5">
      <label for="item-condition" class="text-sm font-medium">
        {{ t('fields.condition') }}
      </label>
      <ChoiceNativeSelect
        id="item-condition"
        v-model="details.condition"
        field="condition"
        optional
      />
    </div>
    <div class="grid gap-1.5">
      <label for="item-completeness" class="text-sm font-medium">
        {{ t('fields.completeness') }}
      </label>
      <ChoiceNativeSelect
        id="item-completeness"
        v-model="details.completeness"
        field="completeness"
        optional
      />
    </div>
    <div class="grid gap-1.5">
      <label for="item-play" class="text-sm font-medium">{{ t('fields.play_status') }}</label>
      <ChoiceNativeSelect
        id="item-play"
        v-model="details.play_status"
        field="play_status"
        optional
      />
    </div>
    <div class="grid gap-1.5">
      <label for="item-location" class="text-sm font-medium">{{ t('fields.location') }}</label>
      <NativeSelect id="item-location" v-model="details.location_id">
        <option value="">{{ t('common.none') }}</option>
        <option v-for="l in locations.data.value ?? []" :key="l.id" :value="l.id">
          {{ l.path }}
        </option>
      </NativeSelect>
    </div>
    <div class="grid gap-1.5">
      <label for="item-owner" class="text-sm font-medium">{{ t('fields.owner') }}</label>
      <NativeSelect id="item-owner" v-model="details.owner_id">
        <option value="">{{ t('common.none') }}</option>
        <option v-for="p in people.data.value ?? []" :key="p.id" :value="p.id">
          {{ p.name }}
        </option>
      </NativeSelect>
    </div>
    <div class="grid gap-1.5">
      <label for="item-acquired" class="text-sm font-medium">
        {{ t('fields.acquired_on') }}
      </label>
      <Input id="item-acquired" v-model="details.acquired_on" type="date" />
    </div>
    <div v-if="perCopy" class="grid gap-1.5">
      <label for="item-price" class="text-sm font-medium">
        {{ t('fields.purchase_price') }}
      </label>
      <Input
        id="item-price"
        v-model="details.purchase_price"
        inputmode="decimal"
        class="font-mono tabular-nums"
        placeholder="0.00"
      />
    </div>
    <div v-if="perCopy" class="grid gap-1.5 sm:col-span-2">
      <label for="item-notes" class="text-sm font-medium">{{ t('fields.notes') }}</label>
      <Textarea id="item-notes" v-model="details.notes" rows="2" />
    </div>
  </div>
</template>
