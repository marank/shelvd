import { createRouter, createWebHistory, type RouteRecordRaw, type Router } from 'vue-router'
import { collect } from '@/addons'
import { useAuthStore } from '@/stores/auth'

declare module 'vue-router' {
  interface RouteMeta {
    /** Reachable without login (login page, public share links). */
    public?: boolean
    /** Which layout App.vue wraps the view in. Default: "app". */
    layout?: 'app' | 'auth' | 'public'
    /** Only for admins (catalog upkeep): others get the "not allowed" page. */
    admin?: boolean
  }
}

/** Each feature adds its routes in router/routes/<feature>.ts (default export); add-ons
 * bring theirs in their `Addon`. */
const modules = import.meta.glob<RouteRecordRaw[]>('./routes/*.ts', {
  eager: true,
  import: 'default',
})
const featureRoutes = Object.values(modules).flat()
/** Every route: the features' and the add-ons' (read when a router is made). */
export const appRoutes = (): RouteRecordRaw[] => [...featureRoutes, ...collect('routes').flat()]

export function installGuard(router: Router): void {
  router.beforeEach((to) => {
    const auth = useAuthStore()
    if (!to.meta.public && !auth.user) {
      return { name: 'login', query: to.fullPath !== '/' ? { next: to.fullPath } : {} }
    }
    if (to.meta.admin && !auth.isAdmin) return { name: 'forbidden' }
    return true
  })
}

const RELOAD_KEY = 'shelvd.chunk-reload'

/** A lazy route's code can't be loaded: after a deploy the old chunk files are gone (or the
 * dev server rebuilt them). Load the target page fresh once; a second failure in a row is
 * a real error and is left to the console. */
export function installChunkReload(
  router: Router,
  reload = (url: string) => window.location.assign(url),
): void {
  router.onError((error, to) => {
    const message = error instanceof Error ? error.message : String(error)
    if (
      !/dynamically imported module|Importing a module script failed|error loading dynamically/i.test(
        message,
      )
    ) {
      throw error
    }
    let last: string | null = null
    try {
      last = sessionStorage.getItem(RELOAD_KEY)
      sessionStorage.setItem(RELOAD_KEY, to.fullPath)
    } catch {
      // storage blocked: reload anyway, the browser's own loop protection is enough
    }
    if (last !== to.fullPath) reload(to.fullPath)
  })
  router.afterEach(() => {
    try {
      sessionStorage.removeItem(RELOAD_KEY)
    } catch {
      // ignore
    }
  })
}

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: appRoutes(),
})
installGuard(router)
installChunkReload(router)

export default router
