import type { RouteRecordRaw } from 'vue-router'

export default [
  {
    path: '/l/:libraryId/loans',
    name: 'loans',
    component: () => import('@/features/manage/views/LoansView.vue'),
  },
  {
    path: '/l/:libraryId/locations',
    name: 'locations',
    component: () => import('@/features/manage/views/LocationsView.vue'),
  },
  {
    path: '/l/:libraryId/locations/new',
    name: 'location-new',
    component: () => import('@/features/manage/views/LocationEditView.vue'),
  },
  {
    path: '/l/:libraryId/locations/:locationId/edit',
    name: 'location-edit',
    component: () => import('@/features/manage/views/LocationEditView.vue'),
  },
  {
    path: '/l/:libraryId/people',
    name: 'people',
    component: () => import('@/features/manage/views/PeopleView.vue'),
  },
  {
    path: '/l/:libraryId/people/new',
    name: 'person-new',
    component: () => import('@/features/manage/views/PersonEditView.vue'),
  },
  {
    path: '/l/:libraryId/people/:personId/edit',
    name: 'person-edit',
    component: () => import('@/features/manage/views/PersonEditView.vue'),
  },
  {
    path: '/l/:libraryId/settings',
    name: 'library-settings',
    component: () => import('@/features/manage/views/LibrarySettingsView.vue'),
  },
] satisfies RouteRecordRaw[]
