<script setup lang="ts">
/** One block of an edit page: explanation on the left, fields on the right (stacked on phones). */
defineProps<{ title: string; description?: string }>()
</script>

<template>
  <section class="grid grid-cols-1 gap-4 py-6 md:grid-cols-[14rem_minmax(0,1fr)] md:gap-8">
    <div>
      <h2 class="text-sm font-semibold">{{ title }}</h2>
      <p v-if="description" class="mt-1 text-sm text-muted-foreground">{{ description }}</p>
    </div>
    <div class="grid grid-cols-1 content-start items-start gap-4 sm:grid-cols-2">
      <slot />
    </div>
  </section>
</template>
