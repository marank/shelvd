<script setup lang="ts">
import type { ButtonHTMLAttributes } from 'vue'
import type { SidebarMenuButtonProps } from './index'
import { cn } from 'cn'
import { Primitive } from 'reka-ui'
import { sidebarMenuButtonVariants } from '.'

// The HTML attributes are ignored as props, so they stay attributes and fall through; listed
// for the template type check (strictTemplates) only.
interface Props extends SidebarMenuButtonProps, /* @vue-ignore */ ButtonHTMLAttributes {}

const props = withDefaults(defineProps<Props>(), {
  as: 'button',
  variant: 'default',
  size: 'default',
})
</script>

<template>
  <Primitive
    data-slot="sidebar-menu-button"
    data-sidebar="menu-button"
    :data-size="size"
    :data-active="isActive || undefined"
    :class="cn(sidebarMenuButtonVariants({ variant, size }), props.class)"
    :as="as"
    :as-child="asChild"
    v-bind="$attrs"
  >
    <slot />
  </Primitive>
</template>
