import type { RouteRecordRaw } from 'vue-router'

/** The three levels by their model and id alone – one game page, focused on the game
 * (work), a release or a copy (item): games and releases show the current library's
 * copies; a copy knows its own library. */
const GamePage = () => import('@/features/game/views/GameView.vue')
export default [
  {
    path: '/works/:workId',
    name: 'work',
    component: GamePage,
  },
  {
    path: '/works/:workId/edit',
    name: 'work-edit',
    component: () => import('@/features/works/views/WorkEditView.vue'),
  },
  {
    path: '/works/:workId/merge',
    name: 'work-merge',
    meta: { admin: true },
    component: () => import('@/features/works/views/MergeWorkView.vue'),
  },
  {
    path: '/releases/new',
    name: 'release-new',
    component: () => import('@/features/add/views/ReleaseNewView.vue'),
  },
  {
    path: '/releases/:releaseId',
    name: 'release',
    component: GamePage,
  },
  {
    path: '/releases/:releaseId/edit',
    name: 'release-edit',
    component: () => import('@/features/works/views/ReleaseEditView.vue'),
  },
  {
    path: '/releases/:releaseId/move',
    name: 'release-move',
    meta: { admin: true },
    component: () => import('@/features/works/views/MoveReleaseView.vue'),
  },
  {
    path: '/items/:itemId',
    name: 'item',
    component: GamePage,
  },
  {
    path: '/items/:itemId/edit',
    name: 'item-edit',
    component: () => import('@/features/items/views/ItemEditView.vue'),
  },
  {
    path: '/items/:itemId/lend',
    name: 'item-lend',
    component: () => import('@/features/items/views/LendView.vue'),
  },
] satisfies RouteRecordRaw[]
