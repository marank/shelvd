import type { RouteRecordRaw } from 'vue-router'
import { TERM_KINDS, isDescribed } from '@/lib/terms'

/** Companies, genres and series: /companies, /companies/<id>, …/edit, …/merge (same for
 * /genres and /series), and for companies and series …/description/<source> (their text
 * from Wikipedia or IGDB) and …/image (a picture from the entries they're linked to).
 * The kind travels in `meta.kind`. */
export default TERM_KINDS.flatMap((kind): RouteRecordRaw[] => [
  {
    path: `/${kind}`,
    name: kind,
    meta: { kind },
    component: () => import('@/features/terms/views/TermsView.vue'),
  },
  {
    path: `/${kind}/:termId`,
    name: `${kind}-detail`,
    meta: { kind },
    component: () => import('@/features/terms/views/TermView.vue'),
  },
  {
    path: `/${kind}/:termId/edit`,
    name: `${kind}-edit`,
    meta: { kind, admin: true },
    component: () => import('@/features/terms/views/TermEditView.vue'),
  },
  {
    path: `/${kind}/:termId/merge`,
    name: `${kind}-merge`,
    meta: { kind, admin: true },
    component: () => import('@/features/terms/views/TermMergeView.vue'),
  },
  ...(isDescribed(kind)
    ? [
        {
          path: `/${kind}/:termId/description/:source`,
          name: `${kind}-description`,
          meta: { kind, admin: true },
          component: () => import('@/features/terms/views/TermDescriptionView.vue'),
        },
        {
          path: `/${kind}/:termId/image`,
          name: `${kind}-image`,
          meta: { kind, admin: true },
          component: () => import('@/features/terms/views/TermImageView.vue'),
        },
      ]
    : []),
])
