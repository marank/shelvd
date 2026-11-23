<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { Button } from '@/components/ui/button'

const { t } = useI18n()
</script>

<template>
  <div class="flex flex-1 flex-col items-center justify-center gap-4 p-10 text-center">
    <p class="font-mono text-5xl font-semibold text-muted-foreground/60">404</p>
    <p class="text-muted-foreground">{{ t('errors.notFound') }}</p>
    <Button as-child variant="outline"
      ><RouterLink to="/">{{ t('actions.back') }}</RouterLink></Button
    >
  </div>
</template>
