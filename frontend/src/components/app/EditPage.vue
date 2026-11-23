<script setup lang="ts">
import { ArrowLeft } from '@lucide/vue'
import { useI18n } from 'vue-i18n'
import type { RouteLocationRaw } from 'vue-router'
import { Button } from '@/components/ui/button'
import { Spinner } from '@/components/ui/spinner'

/**
 * Layout of every edit page: back link and title on top, sections in the middle, a
 * sticky bar with Cancel/Save at the bottom. The default slot goes inside the <form>.
 */
defineProps<{
  title: string
  description?: string
  back: RouteLocationRaw
  busy?: boolean
  saveLabel?: string
  error?: string
}>()
const emit = defineEmits<{ submit: [] }>()
const { t } = useI18n()
</script>

<template>
  <form class="flex min-h-0 flex-1 flex-col" novalidate @submit.prevent="emit('submit')">
    <header class="border-b px-4 py-3 md:px-6">
      <RouterLink
        :to="back"
        class="mb-1 inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
        data-testid="edit-back"
      >
        <ArrowLeft class="size-3.5" /> {{ t('actions.back') }}
      </RouterLink>
      <h1 class="text-lg font-semibold tracking-tight">{{ title }}</h1>
      <p v-if="description" class="text-sm text-muted-foreground">{{ description }}</p>
    </header>
    <div class="flex-1 overflow-y-auto">
      <div class="mx-auto flex max-w-4xl flex-col divide-y px-4 md:px-6">
        <slot />
      </div>
    </div>
    <footer
      class="sticky bottom-0 flex items-center justify-end gap-2 border-t bg-background/90 px-4 py-2.5 backdrop-blur md:px-6"
    >
      <p
        v-if="error"
        class="mr-auto text-sm text-destructive"
        role="alert"
        data-testid="edit-error"
      >
        {{ error }}
      </p>
      <slot name="actions" />
      <Button as-child variant="ghost"
        ><RouterLink :to="back">{{ t('actions.cancel') }}</RouterLink></Button
      >
      <Button type="submit" :disabled="busy" data-testid="edit-save">
        <Spinner v-if="busy" />
        {{ saveLabel ?? t('actions.save') }}
      </Button>
    </footer>
  </form>
</template>
