import type { RouteRecordRaw } from 'vue-router'

export default [
  {
    path: '/login',
    name: 'login',
    component: () => import('@/features/auth/views/LoginView.vue'),
    props: { mode: 'login' },
    meta: { public: true, layout: 'auth' },
  },
  {
    path: '/register',
    name: 'register',
    component: () => import('@/features/auth/views/LoginView.vue'),
    props: { mode: 'register' },
    meta: { public: true, layout: 'auth' },
  },
] satisfies RouteRecordRaw[]
