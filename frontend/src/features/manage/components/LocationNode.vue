<script setup lang="ts">
import { ChevronRight, ListTree, Pencil, Plus, Trash2 } from '@lucide/vue'
import { computed, ref } from 'vue'
import type { RouteLocationRaw } from 'vue-router'
import { useI18n } from 'vue-i18n'
import type { Location } from '@/api/types'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { cn } from '@/lib/utils'
import { KIND_ICONS, type LocationTreeNode } from '../composables/locationTree'

defineOptions({ name: 'LocationNode' })

const props = defineProps<{
  node: LocationTreeNode
  depth: number
  editable: boolean
  collapsed: Set<string>
  /** Id of the node whose inline "add child" form is open. */
  addingTo: string | null
  /** Full "new place" page with this node preset as parent. */
  moreLink: (parent: Location) => RouteLocationRaw
}>()
const emit = defineEmits<{
  toggle: [id: string]
  showItems: [location: Location]
  edit: [location: Location]
  remove: [location: Location]
  startAdd: [id: string | null]
  addChild: [parent: Location, name: string]
}>()

const { t } = useI18n()
const location = computed(() => props.node.location)
const hasChildren = computed(() => props.node.children.length > 0)
const isOpen = computed(() => !props.collapsed.has(location.value.id))
const icon = computed(() => KIND_ICONS[location.value.kind])

const childName = ref('')
function submitChild() {
  const name = childName.value.trim()
  if (!name) return
  emit('addChild', location.value, name)
  childName.value = ''
}
</script>

<template>
  <li :data-testid="`location-${location.id}`">
    <div
      class="group flex min-w-0 flex-wrap items-center gap-1 rounded-md py-1 pr-1 hover:bg-muted/50"
      :style="{ paddingLeft: `${depth * 1.25}rem` }"
    >
      <button
        type="button"
        :class="
          cn(
            'flex size-6 shrink-0 items-center justify-center rounded text-muted-foreground hover:text-foreground',
            !hasChildren && 'invisible',
          )
        "
        :aria-label="t('manage.locations.toggle')"
        :aria-expanded="isOpen"
        data-testid="location-toggle"
        @click="emit('toggle', location.id)"
      >
        <ChevronRight :class="cn('size-4 transition-transform', isOpen && 'rotate-90')" />
      </button>
      <component :is="icon" class="size-4 shrink-0 text-muted-foreground" />
      <span class="min-w-0 flex-1 truncate font-medium" data-testid="location-name">
        {{ location.name }}
      </span>
      <span
        class="font-mono text-xs text-muted-foreground tabular-nums"
        :title="t('manage.locations.directItems')"
        data-testid="location-count"
      >
        {{ t('common.items', location.item_count ?? 0) }}
      </span>
      <div class="flex shrink-0 items-center">
        <Button
          variant="ghost"
          size="xs"
          data-testid="location-items"
          @click="emit('showItems', location)"
        >
          <ListTree />
          <span class="hidden sm:inline">{{ t('manage.locations.showItems') }}</span>
        </Button>
        <template v-if="editable">
          <Button
            variant="ghost"
            size="icon-xs"
            data-testid="location-add-child"
            :aria-label="t('manage.locations.addInside', { name: location.name })"
            @click="emit('startAdd', addingTo === location.id ? null : location.id)"
          >
            <Plus />
          </Button>
          <Button
            variant="ghost"
            size="icon-xs"
            data-testid="location-edit"
            :aria-label="t('actions.edit')"
            @click="emit('edit', location)"
          >
            <Pencil />
          </Button>
          <Button
            variant="ghost"
            size="icon-xs"
            data-testid="location-delete"
            :aria-label="t('actions.delete')"
            @click="emit('remove', location)"
          >
            <Trash2 />
          </Button>
        </template>
      </div>
    </div>
    <form
      v-if="editable && addingTo === location.id"
      class="flex flex-wrap items-center gap-2 py-1"
      :style="{ paddingLeft: `${(depth + 1) * 1.25 + 1.75}rem` }"
      data-testid="child-form"
      @submit.prevent="submitChild"
    >
      <!-- eslint-disable vuejs-accessibility/no-autofocus -- the field opens on the user's own "add place" click -->
      <Input
        v-model="childName"
        class="min-w-0 flex-1 basis-40"
        :placeholder="t('manage.locations.childPlaceholder')"
        :aria-label="t('fields.name')"
        data-testid="child-name"
        autofocus
      />
      <!-- eslint-enable vuejs-accessibility/no-autofocus -->
      <Button type="submit" size="sm" :disabled="!childName.trim()">{{ t('actions.add') }}</Button>
      <Button as-child size="sm" variant="ghost">
        <RouterLink :to="moreLink(location)" data-testid="child-more">
          {{ t('manage.locations.more') }}
        </RouterLink>
      </Button>
      <Button type="button" size="sm" variant="ghost" @click="emit('startAdd', null)">
        {{ t('actions.cancel') }}
      </Button>
    </form>
    <ul v-if="hasChildren && isOpen" role="group">
      <LocationNode
        v-for="child in node.children"
        :key="child.location.id"
        :node="child"
        :depth="depth + 1"
        :editable="editable"
        :collapsed="collapsed"
        :adding-to="addingTo"
        :more-link="moreLink"
        @toggle="emit('toggle', $event)"
        @show-items="emit('showItems', $event)"
        @edit="emit('edit', $event)"
        @remove="emit('remove', $event)"
        @start-add="emit('startAdd', $event)"
        @add-child="(p, n) => emit('addChild', p, n)"
      />
    </ul>
  </li>
</template>
