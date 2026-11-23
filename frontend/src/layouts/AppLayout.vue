<script setup lang="ts">
import { computed, defineAsyncComponent, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { SidebarInset, SidebarProvider } from '@/components/ui/sidebar'
import AppSidebar from '@/components/app/AppSidebar.vue'
import AppTopbar from '@/components/app/AppTopbar.vue'
import ResizeHandle from '@/components/app/ResizeHandle.vue'
import { SIDEBAR_DEFAULT, useUiStore } from '@/stores/ui'

const ui = useUiStore()
const { t } = useI18n()
const dragging = ref(false)
const style = computed(() => ({ '--sidebar-width': `${ui.sidebarWidth}px` }))

// The add dialog (search, scanner) isn't needed at startup: loaded when first opened and
// kept mounted afterwards, so its state survives closing and reopening.
const AddItemDialog = defineAsyncComponent(
  () => import('@/features/add/components/AddItemDialog.vue'),
)
const addLoaded = ref(ui.addOpen)
watch(
  () => ui.addOpen,
  (open) => open && (addLoaded.value = true),
)
</script>

<template>
  <!-- While dragging, the sidebar follows the pointer without its width animation. -->
  <SidebarProvider
    :style="style"
    :class="
      dragging &&
      '**:data-[slot=sidebar-container]:transition-none **:data-[slot=sidebar-gap]:transition-none'
    "
  >
    <AppSidebar>
      <ResizeHandle
        v-model="ui.sidebarWidth"
        edge="right"
        :min="200"
        :max="480"
        :default-width="SIDEBAR_DEFAULT"
        :label="t('layout.resizeSidebar')"
        @dragging="(value) => (dragging = value)"
      />
    </AppSidebar>
    <!-- Fixed to the viewport: each column scrolls by itself, the page never does. -->
    <SidebarInset class="h-svh min-w-0 overflow-hidden">
      <AppTopbar />
      <div class="flex min-h-0 flex-1 flex-col overflow-y-auto">
        <slot />
      </div>
    </SidebarInset>
    <AddItemDialog v-if="addLoaded" />
  </SidebarProvider>
</template>
