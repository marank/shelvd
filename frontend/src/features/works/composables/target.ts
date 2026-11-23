import type { RouteLocationRaw } from 'vue-router'

/** Where to go after a move/merge: that game's page. */
export const workPage = (workId: string): RouteLocationRaw => ({
  name: 'work',
  params: { workId },
})
