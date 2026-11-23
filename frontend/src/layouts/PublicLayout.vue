<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import AppLogo from '@/components/app/AppLogo.vue'
import AppWordmark from '@/components/app/AppWordmark.vue'

const { t } = useI18n()
</script>

<template>
  <div class="min-h-svh bg-background">
    <header class="sticky top-0 z-10 border-b bg-background/85 backdrop-blur">
      <div class="mx-auto flex h-12 max-w-6xl items-center gap-2 px-4">
        <AppLogo class="size-6" />
        <AppWordmark class="h-4 w-auto text-foreground" />
        <span class="text-sm text-muted-foreground">{{ t('app.tagline') }}</span>
      </div>
    </header>
    <main class="mx-auto max-w-6xl px-4 py-6">
      <slot />
    </main>
  </div>
</template>
