import type { RouteRecordRaw } from 'vue-router'

export default [
  {
    path: '/',
    name: 'home',
    component: () => import('@/features/library/views/HomeView.vue'),
  },
  {
    path: '/libraries',
    name: 'libraries',
    component: () => import('@/features/library/views/LibrariesView.vue'),
  },
  {
    path: '/l/:libraryId',
    name: 'explorer',
    component: () => import('@/features/explorer/views/ExplorerView.vue'),
  },
  {
    path: '/l/:libraryId/views/new',
    name: 'overview-new',
    component: () => import('@/features/explorer/views/OverviewEditView.vue'),
  },
  {
    path: '/l/:libraryId/views/:overviewId/edit',
    name: 'overview-edit',
    component: () => import('@/features/explorer/views/OverviewEditView.vue'),
  },
  {
    path: '/forbidden',
    name: 'forbidden',
    component: () => import('@/features/library/views/ForbiddenView.vue'),
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'not-found',
    component: () => import('@/features/library/views/NotFoundView.vue'),
    meta: { public: true },
  },
] satisfies RouteRecordRaw[]
