import type { RouteRecordRaw } from 'vue-router'

export default [
  {
    path: '/catalog/review',
    name: 'catalog-review',
    meta: { admin: true },
    component: () => import('@/features/review/views/ReviewView.vue'),
  },
] satisfies RouteRecordRaw[]
