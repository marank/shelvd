<script setup lang="ts">
import {
  BookMarked,
  ChevronsUpDown,
  CalendarClock,
  ClipboardCheck,
  Code,
  Database,
  Gamepad2,
  HandCoins,
  Library as LibraryIcon,
  ListChecks,
  LogOut,
  MapPin,
  Plus,
  Settings,
  Users,
} from '@lucide/vue'
import { LICENSE_NAME, SOURCE_URL } from '@/lib/source'
import { TERM_ICONS, TERM_KINDS, termList } from '@/lib/terms'
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuBadge,
  SidebarMenuButton,
  SidebarMenuItem,
} from '@/components/ui/sidebar'
import { collect, type AddonLink } from '@/addons'
import AppLogo from '@/components/app/AppLogo.vue'
import AppWordmark from '@/components/app/AppWordmark.vue'
import ThemeMenu from '@/components/app/ThemeMenu.vue'
import { useCurrentLibrary } from '@/features/library/composables/useCurrentLibrary'
import SidebarViews from '@/features/explorer/components/SidebarViews.vue'
import { useAuthStore } from '@/stores/auth'
import { canEdit } from '@/features/library/composables/useLibraries'
import { useReviewCount } from '@/features/review/composables/useReview'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const { id: libraryId, library, libraries } = useCurrentLibrary()
async function logout() {
  await auth.logout()
  void router.push({ name: 'login' })
}

const reviewCount = useReviewCount()
// Who borrowed what is for those who look after the library.
const manageLinks = computed(() => [
  ...(canEdit(library.value?.role)
    ? [{ name: 'loans', icon: HandCoins, label: t('nav.loans') }]
    : []),
  { name: 'locations', icon: MapPin, label: t('nav.locations') },
  { name: 'people', icon: Users, label: t('nav.people') },
  { name: 'library-settings', icon: Settings, label: t('nav.settings') },
])

/** Links that add-ons put into the sidebar and the user menu. */
const addonNav = collect('nav').flat()
const addonAccountMenu = collect('accountMenu').flat()
const isActive = (link: AddonLink) =>
  route.name === link.route || (link.activeOn ?? []).includes(String(route.name))
</script>

<template>
  <Sidebar collapsible="offcanvas">
    <SidebarHeader>
      <!-- Same height and bottom border as the topbar, so both read as one line. -->
      <RouterLink
        :to="{ name: 'home' }"
        class="-mx-2 -mt-2 flex h-12 shrink-0 items-center gap-2 border-b px-4"
        data-testid="sidebar-brand"
      >
        <AppLogo class="size-7 shrink-0" />
        <AppWordmark class="h-5 w-auto text-foreground" />
      </RouterLink>
      <DropdownMenu>
        <DropdownMenuTrigger as-child>
          <SidebarMenuButton size="lg" data-testid="library-switcher">
            <div
              class="flex size-8 shrink-0 items-center justify-center rounded-md border bg-background"
            >
              <LibraryIcon class="size-4" />
            </div>
            <div class="grid min-w-0 flex-1 text-left leading-tight">
              <span class="truncate text-sm font-semibold">{{
                library?.name ?? t('nav.library')
              }}</span>
              <span class="truncate font-mono text-[11px] text-muted-foreground">
                <template v-if="library">
                  {{ t('common.items', { n: library.item_count }, library.item_count) }} ·
                  {{ t(`choices.role.${library.role}`) }}
                </template>
              </span>
            </div>
            <ChevronsUpDown class="size-4 text-muted-foreground" />
          </SidebarMenuButton>
        </DropdownMenuTrigger>
        <DropdownMenuContent class="w-64" align="start">
          <DropdownMenuLabel>{{ t('nav.switchLibrary') }}</DropdownMenuLabel>
          <DropdownMenuItem
            v-for="lib in libraries.data.value ?? []"
            :key="lib.id"
            @select="router.push({ name: 'explorer', params: { libraryId: lib.id } })"
          >
            <LibraryIcon class="size-4" />
            <span class="flex-1 truncate">{{ lib.name }}</span>
            <span class="font-mono text-[11px] text-muted-foreground">{{ lib.item_count }}</span>
          </DropdownMenuItem>
          <DropdownMenuSeparator />
          <DropdownMenuItem @select="router.push({ name: 'home', query: { new: '1' } })">
            <Plus class="size-4" /> {{ t('nav.newLibrary') }}
          </DropdownMenuItem>
          <DropdownMenuItem
            data-testid="manage-libraries"
            @select="router.push({ name: 'libraries' })"
          >
            <Settings class="size-4" /> {{ t('nav.manageLibraries') }}
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </SidebarHeader>

    <SidebarContent v-if="libraryId">
      <SidebarViews :library-id="libraryId" />

      <SidebarGroup>
        <SidebarGroupLabel>{{ t('nav.manage') }}</SidebarGroupLabel>
        <SidebarMenu>
          <SidebarMenuItem v-for="link in manageLinks" :key="link.name">
            <SidebarMenuButton as-child :is-active="route.name === link.name">
              <RouterLink :to="{ name: link.name, params: { libraryId } }">
                <component :is="link.icon" class="size-4" />
                <span>{{ link.label }}</span>
              </RouterLink>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarGroup>

      <SidebarGroup>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton as-child :is-active="route.name === 'upcoming'">
              <RouterLink :to="{ name: 'upcoming' }" data-testid="nav-upcoming">
                <CalendarClock class="size-4" />
                <span>{{ t('nav.upcoming') }}</span>
              </RouterLink>
            </SidebarMenuButton>
          </SidebarMenuItem>
          <SidebarMenuItem v-for="link in addonNav" :key="link.route">
            <SidebarMenuButton as-child :is-active="isActive(link)">
              <RouterLink :to="{ name: link.route }" :data-testid="link.testid">
                <component :is="link.icon" class="size-4" />
                <span>{{ t(link.label) }}</span>
              </RouterLink>
            </SidebarMenuButton>
          </SidebarMenuItem>
          <SidebarMenuItem>
            <SidebarMenuButton
              as-child
              :is-active="route.name === 'lists' || route.name === 'list-detail'"
            >
              <RouterLink :to="{ name: 'lists' }">
                <ListChecks class="size-4" />
                <span>{{ t('nav.lists') }}</span>
              </RouterLink>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarGroup>
      <SidebarGroup>
        <SidebarGroupLabel>{{ t('nav.catalog') }}</SidebarGroupLabel>
        <SidebarMenu>
          <SidebarMenuItem v-if="auth.isAdmin">
            <SidebarMenuButton as-child :is-active="route.name === 'catalog-review'">
              <RouterLink :to="{ name: 'catalog-review' }" data-testid="nav-review">
                <ClipboardCheck class="size-4" />
                <span>{{ t('nav.review') }}</span>
              </RouterLink>
            </SidebarMenuButton>
            <SidebarMenuBadge v-if="reviewCount.data.value?.count" data-testid="review-count">
              {{ reviewCount.data.value.count }}
            </SidebarMenuBadge>
          </SidebarMenuItem>
          <SidebarMenuItem>
            <SidebarMenuButton
              as-child
              :is-active="String(route.name ?? '').startsWith('platform')"
            >
              <RouterLink :to="{ name: 'platforms' }" data-testid="nav-platforms">
                <Gamepad2 class="size-4" />
                <span>{{ t('nav.platforms') }}</span>
              </RouterLink>
            </SidebarMenuButton>
          </SidebarMenuItem>
          <SidebarMenuItem v-for="kind in TERM_KINDS" :key="kind">
            <SidebarMenuButton as-child :is-active="route.meta.kind === kind">
              <RouterLink :to="termList(kind)" :data-testid="`nav-${kind}`">
                <component :is="TERM_ICONS[kind]" class="size-4" />
                <span>{{ t(`nav.${kind}`) }}</span>
              </RouterLink>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarGroup>
    </SidebarContent>

    <SidebarFooter>
      <SidebarMenu>
        <SidebarMenuItem>
          <SidebarMenuButton as-child size="sm" :is-active="route.name === 'libraries'">
            <RouterLink :to="{ name: 'libraries' }" data-testid="nav-libraries">
              <LibraryIcon class="size-4" />
              <span>{{ t('nav.libraries') }}</span>
            </RouterLink>
          </SidebarMenuButton>
        </SidebarMenuItem>
        <SidebarMenuItem>
          <SidebarMenuButton
            as-child
            size="sm"
            :is-active="route.name === 'integrations' || route.name === 'integration-edit'"
          >
            <RouterLink :to="{ name: 'integrations' }">
              <Database class="size-4" />
              <span>{{ t('nav.integrations') }}</span>
            </RouterLink>
          </SidebarMenuButton>
        </SidebarMenuItem>
        <SidebarMenuItem>
          <DropdownMenu>
            <DropdownMenuTrigger as-child>
              <SidebarMenuButton data-testid="user-menu">
                <BookMarked class="size-4" />
                <span class="flex-1 truncate">{{ auth.user?.username }}</span>
                <ChevronsUpDown class="size-4 text-muted-foreground" />
              </SidebarMenuButton>
            </DropdownMenuTrigger>
            <DropdownMenuContent side="top" align="start" class="w-56">
              <ThemeMenu />
              <DropdownMenuSeparator />
              <DropdownMenuItem v-for="link in addonAccountMenu" :key="link.route" as-child>
                <RouterLink :to="{ name: link.route }" :data-testid="link.testid">
                  <component :is="link.icon" class="size-4" /> {{ t(link.label) }}
                </RouterLink>
              </DropdownMenuItem>
              <DropdownMenuItem as-child>
                <a
                  :href="SOURCE_URL"
                  target="_blank"
                  rel="noopener noreferrer"
                  data-testid="source-code"
                >
                  <Code class="size-4" /> {{ t('source.code') }} ({{ LICENSE_NAME }})
                </a>
              </DropdownMenuItem>
              <DropdownMenuItem @select="logout">
                <LogOut class="size-4" /> {{ t('actions.logout') }}
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </SidebarMenuItem>
      </SidebarMenu>
    </SidebarFooter>
    <!-- The resize handle (from the layout) sits on the sidebar's right edge. -->
    <slot />
  </Sidebar>
</template>
