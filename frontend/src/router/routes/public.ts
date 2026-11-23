import type { RouteRecordRaw } from 'vue-router'

export default [
  {
    path: '/share/:token',
    name: 'public-library',
    component: () => import('@/features/public/views/PublicLibraryView.vue'),
    meta: { public: true, layout: 'public' },
  },
  {
    path: '/share/list/:token',
    name: 'public-list',
    component: () => import('@/features/public/views/PublicListView.vue'),
    meta: { public: true, layout: 'public' },
  },
] satisfies RouteRecordRaw[]
