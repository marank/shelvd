<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { LICENSE_NAME, SOURCE_URL } from '@/lib/source'

/** "shelvd is free software (AGPL-3.0) · Source code" – the AGPL's offer of the source. */
const { t } = useI18n()
</script>

<template>
  <p class="text-center text-xs text-muted-foreground" data-testid="source-link">
    {{ t('source.freeSoftware', { license: LICENSE_NAME }) }} ·
    <a
      :href="SOURCE_URL"
      target="_blank"
      rel="noopener noreferrer"
      class="underline underline-offset-4 hover:text-foreground"
    >
      {{ t('source.code') }}
    </a>
  </p>
</template>
