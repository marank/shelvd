import type { RouteRecordRaw } from 'vue-router'

export default [
  {
    path: '/catalog/platforms',
    name: 'platforms',
    component: () => import('@/features/platforms/views/PlatformsView.vue'),
  },
  {
    path: '/platforms/:platformId',
    name: 'platforms-detail',
    meta: { kind: 'platforms' },
    props: true,
    component: () => import('@/features/platforms/views/PlatformView.vue'),
  },
  {
    path: '/platforms/:platformId/description/:source',
    name: 'platforms-description',
    meta: { kind: 'platforms', admin: true },
    component: () => import('@/features/terms/views/TermDescriptionView.vue'),
  },
  {
    path: '/platforms/:platformId/image',
    name: 'platforms-image',
    meta: { kind: 'platforms', admin: true },
    component: () => import('@/features/terms/views/TermImageView.vue'),
  },
  {
    path: '/catalog/platforms/new',
    name: 'platform-new',
    meta: { admin: true },
    component: () => import('@/features/platforms/views/PlatformEditView.vue'),
  },
  {
    path: '/catalog/platforms/:platformId/edit',
    name: 'platform-edit',
    meta: { admin: true },
    component: () => import('@/features/platforms/views/PlatformEditView.vue'),
  },
] satisfies RouteRecordRaw[]
