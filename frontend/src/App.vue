<script setup lang="ts">
import { useMediaQuery } from '@vueuse/core'
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { Toaster } from '@/components/ui/sonner'
import AppLayout from '@/layouts/AppLayout.vue'
import AuthLayout from '@/layouts/AuthLayout.vue'
import PublicLayout from '@/layouts/PublicLayout.vue'

const route = useRoute()
const layouts = { app: AppLayout, auth: AuthLayout, public: PublicLayout }
const layout = computed(() => layouts[route.meta.layout ?? 'app'])
// On phones the bottom holds the main buttons (scanner, save bars): toasts go on top.
const phone = useMediaQuery('(max-width: 639.98px)')
</script>

<template>
  <component :is="layout">
    <RouterView />
  </component>
  <Toaster :position="phone ? 'top-center' : 'bottom-right'" rich-colors />
</template>
