import type { RouteRecordRaw } from 'vue-router'

export default [
  {
    path: '/integrations',
    name: 'integrations',
    component: () => import('@/features/integrations/views/IntegrationsView.vue'),
  },
  {
    path: '/integrations/:key',
    name: 'integration-edit',
    meta: { admin: true },
    component: () => import('@/features/integrations/views/IntegrationEditView.vue'),
  },
  {
    path: '/works/:workId/facts/:source',
    name: 'fact-match',
    meta: { admin: true },
    component: () => import('@/features/integrations/views/FactMatchView.vue'),
  },
  {
    path: '/works/:workId/metadata/:source',
    name: 'metadata-match',
    meta: { admin: true },
    component: () => import('@/features/integrations/views/MetadataMatchView.vue'),
  },
  {
    path: '/works/:workId/metadata/:source/:externalId',
    name: 'metadata-review',
    meta: { admin: true },
    component: () => import('@/features/integrations/views/MetadataReviewView.vue'),
  },
  {
    path: '/releases/:releaseId/covers',
    name: 'cover-search',
    component: () => import('@/features/integrations/views/CoverSearchView.vue'),
  },
] satisfies RouteRecordRaw[]
