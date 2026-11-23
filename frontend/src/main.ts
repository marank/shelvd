import './assets/main.css'

import { VueQueryPlugin, QueryClient } from '@tanstack/vue-query'
import { createPinia } from 'pinia'
import { createApp } from 'vue'

import { ensureCsrf } from './api/csrf'
import { setApiLanguage, setUnauthorizedHandler } from './api/client'
import App from './App.vue'
import { i18n, loadLocale } from './i18n'
import router from './router'
import { useAuthStore } from './stores/auth'
import { useUiStore } from './stores/ui'

const app = createApp(App)
const pinia = createPinia()
const queryClient = new QueryClient({
  defaultOptions: { queries: { staleTime: 30_000, retry: 1, refetchOnWindowFocus: false } },
})
app.use(pinia)
app.use(i18n)
app.use(VueQueryPlugin, { queryClient })

setApiLanguage(i18n.global.locale.value)
document.documentElement.lang = i18n.global.locale.value
useUiStore().apply()

const auth = useAuthStore()
setUnauthorizedHandler(() => {
  auth.clear()
  queryClient.clear()
  const current = router.currentRoute.value
  if (!current.meta.public) void router.push({ name: 'login', query: { next: current.fullPath } })
})

await Promise.all([loadLocale(i18n.global.locale.value), ensureCsrf()])
await auth.fetchMe().catch(() => null)
app.use(router)
app.mount('#app')
