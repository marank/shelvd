<script setup lang="ts">
import type { PrimitiveProps } from 'reka-ui'
import type { ButtonHTMLAttributes, HTMLAttributes } from 'vue'
import { cn } from 'cn'
import { Primitive } from 'reka-ui'

// The HTML attributes are ignored as props, so they stay attributes and fall through; listed
// for the template type check (strictTemplates) only.
interface Props extends PrimitiveProps, /* @vue-ignore */ ButtonHTMLAttributes {
  class?: HTMLAttributes['class']
}

const props = defineProps<Props>()
</script>

<template>
  <Primitive
    data-slot="sidebar-group-action"
    data-sidebar="group-action"
    :as="as"
    :as-child="asChild"
    :class="
      cn(
        'text-sidebar-foreground ring-sidebar-ring hover:bg-sidebar-accent hover:text-sidebar-accent-foreground absolute top-3.5 right-3 w-5 rounded-md p-0 focus-visible:ring-2 [&>svg]:size-4 flex aspect-square items-center justify-center outline-hidden transition-transform group-data-[collapsible=icon]:hidden after:absolute after:-inset-2 md:after:hidden [&>svg]:shrink-0',
        props.class,
      )
    "
  >
    <slot />
  </Primitive>
</template>
