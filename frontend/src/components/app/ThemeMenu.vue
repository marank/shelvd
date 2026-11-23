<script setup lang="ts">
import { Monitor, Moon, Sun } from '@lucide/vue'
import { useI18n } from 'vue-i18n'
import {
  DropdownMenuLabel,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
} from '@/components/ui/dropdown-menu'
import { LOCALES, setLocale, type Locale } from '@/i18n'
import { useUiStore, type Theme } from '@/stores/ui'

const ui = useUiStore()
const { t, locale } = useI18n()
const themes: { value: Theme; icon: typeof Sun }[] = [
  { value: 'system', icon: Monitor },
  { value: 'light', icon: Sun },
  { value: 'dark', icon: Moon },
]
</script>

<template>
  <DropdownMenuLabel>{{ t('theme.label') }}</DropdownMenuLabel>
  <DropdownMenuRadioGroup
    :model-value="ui.theme"
    @update:model-value="(v) => ui.setTheme(v as Theme)"
  >
    <DropdownMenuRadioItem v-for="th in themes" :key="th.value" :value="th.value">
      <component :is="th.icon" class="size-4" />
      {{ t(`theme.${th.value}`) }}
    </DropdownMenuRadioItem>
  </DropdownMenuRadioGroup>
  <DropdownMenuLabel>{{ t('language.label') }}</DropdownMenuLabel>
  <DropdownMenuRadioGroup :model-value="locale" @update:model-value="(v) => setLocale(v as Locale)">
    <DropdownMenuRadioItem v-for="lang in LOCALES" :key="lang" :value="lang">
      {{ t(`language.${lang}`) }}
    </DropdownMenuRadioItem>
  </DropdownMenuRadioGroup>
</template>
