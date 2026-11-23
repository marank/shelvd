<script setup lang="ts" generic="T extends StringOrNumber">
import type { StringOrNumber, TabsRootEmits, TabsRootProps } from 'reka-ui'
import type { HTMLAttributes } from 'vue'
import { reactiveOmit } from '@vueuse/core'
import { cn } from 'cn'
import { TabsRoot, useForwardPropsEmits } from 'reka-ui'

const props = defineProps<TabsRootProps<T> & { class?: HTMLAttributes['class'] }>()
const emits = defineEmits<TabsRootEmits<T>>()

const delegatedProps = reactiveOmit(props, 'class')
const forwarded = useForwardPropsEmits(delegatedProps, emits)
</script>

<template>
  <TabsRoot
    v-slot="slotProps"
    data-slot="tabs"
    :data-orientation="props.orientation ?? 'horizontal'"
    v-bind="forwarded"
    :class="cn('gap-2 group/tabs flex data-horizontal:flex-col', props.class)"
  >
    <slot v-bind="slotProps" />
  </TabsRoot>
</template>
