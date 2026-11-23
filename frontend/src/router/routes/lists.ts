import type { RouteRecordRaw } from 'vue-router'

export default [
  {
    path: '/lists',
    name: 'lists',
    component: () => import('@/features/lists/views/ListsView.vue'),
  },
  {
    path: '/lists/new',
    name: 'list-new',
    component: () => import('@/features/lists/views/ListEditView.vue'),
  },
  {
    path: '/lists/:listId',
    name: 'list-detail',
    component: () => import('@/features/lists/views/ListDetailView.vue'),
  },
  {
    path: '/lists/:listId/edit',
    name: 'list-edit',
    component: () => import('@/features/lists/views/ListEditView.vue'),
  },
] satisfies RouteRecordRaw[]
