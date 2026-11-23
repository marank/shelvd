<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import AppLogo from '@/components/app/AppLogo.vue'
import AppWordmark from '@/components/app/AppWordmark.vue'

const { t } = useI18n()
</script>

<template>
  <div class="relative flex min-h-svh flex-col items-center justify-center gap-8 bg-background p-4">
    <!-- A faint grid: the "technical" note of the app, kept quiet. -->
    <div
      aria-hidden="true"
      class="pointer-events-none absolute inset-0 [background-image:linear-gradient(to_right,var(--border)_1px,transparent_1px),linear-gradient(to_bottom,var(--border)_1px,transparent_1px)] [background-size:32px_32px] [mask-image:radial-gradient(ellipse_at_center,black_20%,transparent_70%)] opacity-60"
    />
    <div class="relative flex flex-col items-center gap-3">
      <AppLogo class="size-24 sm:size-28" />
      <!-- eslint-disable-next-line vuejs-accessibility/heading-has-content -- the wordmark is an <svg role="img" aria-label="shelvd"> -->
      <h1 class="text-foreground">
        <AppWordmark class="h-11 w-auto sm:h-14" />
      </h1>
      <p class="text-sm text-muted-foreground">{{ t('app.tagline') }}</p>
    </div>
    <div class="relative w-full max-w-sm">
      <slot />
    </div>
  </div>
</template>
