<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'

/** Select for optional values; "" means "not set" (Reka's Select can't hold ""). */
const NONE = '__none'
const props = defineProps<{
  id?: string
  modelValue: string | null | undefined
  options: { value: string; label: string }[]
  optional?: boolean
}>()
const emit = defineEmits<{ 'update:modelValue': [value: string | null] }>()
const { t } = useI18n()

function update(value: unknown) {
  emit('update:modelValue', value === NONE ? null : String(value))
}
</script>

<template>
  <!-- eslint-disable-next-line vuejs-accessibility/form-control-has-label -- the root only holds the value; the trigger carries the id the label points to -->
  <Select :model-value="props.modelValue || NONE" @update:model-value="update">
    <SelectTrigger :id="id" class="w-full">
      <SelectValue />
    </SelectTrigger>
    <SelectContent>
      <SelectItem v-if="optional" :value="NONE">{{ t('common.none') }}</SelectItem>
      <SelectItem v-for="option in options" :key="option.value" :value="option.value">
        {{ option.label }}
      </SelectItem>
    </SelectContent>
  </Select>
</template>
