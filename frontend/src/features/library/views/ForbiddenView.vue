<script setup lang="ts">
// Reached through an admin-only page (or a link from before roles changed).
import { ShieldOff } from '@lucide/vue'
import { useI18n } from 'vue-i18n'
import { Button } from '@/components/ui/button'

const { t } = useI18n()
</script>

<template>
  <div
    class="flex flex-1 flex-col items-center justify-center gap-4 p-10 text-center"
    data-testid="forbidden"
  >
    <ShieldOff class="size-10 text-muted-foreground/60" />
    <p class="max-w-sm text-muted-foreground">{{ t('errors.forbidden') }}</p>
    <Button as-child variant="outline"
      ><RouterLink to="/">{{ t('actions.back') }}</RouterLink></Button
    >
  </div>
</template>
