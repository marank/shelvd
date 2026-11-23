<script setup lang="ts" generic="V extends string">
import { useI18n } from 'vue-i18n'
import NativeSelect from '@/components/app/NativeSelect.vue'
import { CHOICES } from './options'

/** A native select over one of the copy's choice fields; `optional` adds "none" (""). The
 * id and other attributes go to the <select>. */
defineProps<{ field: keyof typeof CHOICES; optional?: boolean }>()
const model = defineModel<V>({ required: true })
const { t } = useI18n()
</script>

<template>
  <NativeSelect v-model="model">
    <option v-if="optional" value="">{{ t('common.none') }}</option>
    <option v-for="v in CHOICES[field]" :key="v" :value="v">
      {{ t(`choices.${field}.${v}`) }}
    </option>
  </NativeSelect>
</template>
