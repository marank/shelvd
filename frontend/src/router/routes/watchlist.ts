import type { RouteRecordRaw } from 'vue-router'

export default [
  {
    path: '/upcoming',
    name: 'upcoming',
    component: () => import('@/features/watchlist/views/UpcomingView.vue'),
  },
  {
    path: '/watchlist/new',
    name: 'tracking-new',
    component: () => import('@/features/watchlist/views/WatchlistEditView.vue'),
  },
  {
    path: '/watchlist/:trackingId/edit',
    name: 'tracking-edit',
    component: () => import('@/features/watchlist/views/WatchlistEditView.vue'),
  },
  {
    path: '/watchlist/:trackingId/take-over',
    name: 'take-over',
    component: () => import('@/features/watchlist/views/TakeOverView.vue'),
  },
] satisfies RouteRecordRaw[]
