<script setup lang="ts">
import type { PrimitiveProps } from 'reka-ui'
import type { HTMLAttributes } from 'vue'
import type { BadgeVariants } from '.'
import { reactiveOmit } from '@vueuse/core'
import { cn } from 'cn'
import { Primitive } from 'reka-ui'
import { badgeVariants } from '.'

// The HTML attributes are ignored as props, so they stay attributes and fall through; listed
// for the template type check (strictTemplates) only.
interface Props extends PrimitiveProps, /* @vue-ignore */ HTMLAttributes {
  variant?: BadgeVariants['variant']
  class?: HTMLAttributes['class']
}

const props = defineProps<Props>()

const delegatedProps = reactiveOmit(props, 'class')
</script>

<template>
  <Primitive
    data-slot="badge"
    :data-variant="variant"
    :class="cn(badgeVariants({ variant }), props.class)"
    v-bind="delegatedProps"
  >
    <slot />
  </Primitive>
</template>
