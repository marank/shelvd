<script setup lang="ts">
import {
  EllipsisVertical,
  FolderTree,
  Pencil,
  Plus,
  SlidersHorizontal,
  TextCursorInput,
  Trash2,
} from '@lucide/vue'
import { computed, defineAsyncComponent, nextTick, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import {
  SidebarGroup,
  SidebarGroupAction,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuAction,
  SidebarMenuButton,
  SidebarMenuItem,
} from '@/components/ui/sidebar'
import type { Overview } from '@/api/types'
import { useLastView, useOverviews, useSaveOverview } from '../composables/useOverviews'
import { useTree } from '../composables/useItems'
import GroupTree from './GroupTree.vue'

const DeleteViewDialog = defineAsyncComponent(() => import('./DeleteViewDialog.vue'))

/** The sidebar's saved views: open one, its folder tree below the active one, and – on
 * hover – a menu to edit, rename or delete it and a + to create a new one. */
const props = defineProps<{ libraryId: string }>()
const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const overviews = useOverviews(() => props.libraryId)
const save = useSaveOverview(() => props.libraryId)

const onExplorer = computed(() => route.name === 'explorer')
const lastView = useLastView(() => props.libraryId)
/** On the explorer its view (`v`), elsewhere the view last opened in this library. */
const activeOverviewId = computed(() => {
  const v = route.query.v
  const all = overviews.data.value ?? []
  const fromUrl =
    onExplorer.value && typeof v === 'string' ? all.find((o) => o.id === v) : undefined
  return (fromUrl ?? lastView.value)?.id
})
const activeOverview = computed(() =>
  overviews.data.value?.find((o) => o.id === activeOverviewId.value),
)
const groupBy = computed(() => {
  const g = route.query.g
  if (onExplorer.value && typeof g === 'string') return g.split(',').filter(Boolean)
  return activeOverview.value?.group_by ?? []
})
const tree = useTree(
  () => props.libraryId,
  () => ({
    groupBy: groupBy.value,
    q: '',
    filters: [],
    where: activeOverview.value?.filters ?? [],
    match: activeOverview.value?.match ?? 'all',
  }),
)
const activePath = computed(() => {
  const p = route.query.p
  return onExplorer.value ? (Array.isArray(p) ? p : p ? [p] : []).map(String) : []
})

function openOverview(id: string) {
  void router.push({ name: 'explorer', params: { libraryId: props.libraryId }, query: { v: id } })
}

function openPath(path: string[]) {
  void router.push({
    name: 'explorer',
    params: { libraryId: props.libraryId },
    query: {
      ...(onExplorer.value ? route.query : { v: activeOverviewId.value }),
      p: path,
    },
  })
}

// --- rename in place ---------------------------------------------------------------------
const renamingId = ref<string | null>(null)
const draft = ref('')

function startRename(overview: Overview) {
  renamingId.value = overview.id
  draft.value = overview.name
  // After the menu has closed and handed focus back, so the input keeps it.
  setTimeout(() => {
    const input = document.querySelector<HTMLInputElement>('[data-testid="rename-view-input"]')
    input?.focus()
    input?.select()
  }, 0)
}

async function finishRename() {
  const id = renamingId.value
  if (!id) return
  renamingId.value = null
  const name = draft.value.trim()
  const overview = overviews.data.value?.find((o) => o.id === id)
  if (!overview || !name || name === overview.name) return
  await save.update.mutateAsync({ id, body: { name } })
}

function cancelRename() {
  renamingId.value = null
}

// --- delete ------------------------------------------------------------------------------
const deleting = ref<Overview | null>(null)
const canDelete = computed(() => (overviews.data.value?.length ?? 0) > 1)

async function confirmDelete() {
  const overview = deleting.value
  if (!overview) return
  await save.remove.mutateAsync(overview.id)
  deleting.value = null
  if (onExplorer.value && overview.id === activeOverviewId.value) {
    await nextTick()
    void router.push({ name: 'explorer', params: { libraryId: props.libraryId } })
  }
}
</script>

<template>
  <SidebarGroup class="group/views">
    <SidebarGroupLabel>{{ t('nav.overviews') }}</SidebarGroupLabel>
    <SidebarGroupAction
      as-child
      class="opacity-100 md:opacity-0 group-hover/views:opacity-100 focus-visible:opacity-100"
      :title="t('explorer.newView')"
    >
      <RouterLink
        :to="{ name: 'overview-new', params: { libraryId } }"
        :aria-label="t('explorer.newView')"
        data-testid="new-view"
      >
        <Plus />
      </RouterLink>
    </SidebarGroupAction>
    <SidebarMenu>
      <SidebarMenuItem v-for="o in overviews.data.value ?? []" :key="o.id">
        <div
          v-if="renamingId === o.id"
          class="flex h-8 items-center gap-2 rounded-md px-2 ring-2 ring-sidebar-ring"
        >
          <FolderTree class="size-4 shrink-0" />
          <input
            v-model="draft"
            class="min-w-0 flex-1 bg-transparent text-sm outline-none"
            :aria-label="t('explorer.renameView')"
            data-testid="rename-view-input"
            @keydown.enter.prevent="finishRename"
            @keydown.esc.prevent="cancelRename"
            @blur="finishRename"
          />
        </div>
        <template v-else>
          <SidebarMenuButton
            :is-active="onExplorer && o.id === activeOverviewId && !activePath.length"
            class="pr-8"
            @click="openOverview(o.id)"
          >
            <FolderTree class="size-4" />
            <span class="truncate">{{ o.name }}</span>
          </SidebarMenuButton>
          <DropdownMenu>
            <DropdownMenuTrigger as-child>
              <SidebarMenuAction
                show-on-hover
                :aria-label="t('explorer.viewActions', { name: o.name })"
                :data-testid="`view-actions-${o.id}`"
              >
                <EllipsisVertical />
              </SidebarMenuAction>
            </DropdownMenuTrigger>
            <DropdownMenuContent side="right" align="start" class="w-56">
              <DropdownMenuItem as-child>
                <RouterLink
                  :to="{ name: 'overview-edit', params: { libraryId, overviewId: o.id } }"
                  data-testid="sidebar-edit-view"
                >
                  <Pencil class="size-4" /> {{ t('actions.edit') }}
                </RouterLink>
              </DropdownMenuItem>
              <DropdownMenuItem data-testid="sidebar-rename-view" @select="startRename(o)">
                <TextCursorInput class="size-4" /> {{ t('explorer.renameView') }}
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem
                variant="destructive"
                :disabled="!canDelete"
                data-testid="sidebar-delete-view"
                @select="deleting = o"
              >
                <Trash2 class="size-4" />
                <span class="flex flex-col">
                  {{ t('actions.delete') }}
                  <span v-if="!canDelete" class="text-[11px] text-muted-foreground">
                    {{ t('explorer.lastView') }}
                  </span>
                </span>
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </template>
        <div
          v-if="o.id === activeOverviewId && groupBy.length && tree.data.value?.nodes.length"
          class="mt-0.5 mb-1 ml-2 border-l pl-1"
          data-testid="sidebar-tree"
        >
          <GroupTree :nodes="tree.data.value.nodes" :active="activePath" @open="openPath" />
        </div>
      </SidebarMenuItem>
      <SidebarMenuItem v-if="!overviews.data.value?.length">
        <SidebarMenuButton @click="router.push({ name: 'explorer', params: { libraryId } })">
          <SlidersHorizontal class="size-4" />
          <span>{{ t('nav.allItems') }}</span>
        </SidebarMenuButton>
      </SidebarMenuItem>
    </SidebarMenu>

    <DeleteViewDialog
      v-if="deleting"
      :name="deleting.name"
      @confirm="confirmDelete"
      @cancel="deleting = null"
    />
  </SidebarGroup>
</template>
