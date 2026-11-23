import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { User } from '@/api/types'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(null)
  /** Keeps the shared catalog (and the review queue, integrations). */
  const isAdmin = computed(() => !!user.value?.is_staff)
  /** May add games to the catalog (unreviewed until an admin approves them). */
  const canContribute = computed(() => !!user.value?.can_contribute)

  async function fetchMe(): Promise<User | null> {
    const { data } = await api.GET('/api/auth/me')
    user.value = data ?? null
    return user.value
  }

  async function login(username: string, password: string): Promise<User> {
    user.value = await unwrap(api.POST('/api/auth/login', { body: { username, password } }))
    return user.value
  }

  async function register(username: string, password: string, email = ''): Promise<User> {
    user.value = await unwrap(
      api.POST('/api/auth/register', { body: { username, password, email } }),
    )
    return user.value
  }

  async function logout(): Promise<void> {
    await api.POST('/api/auth/logout')
    user.value = null
  }

  function clear(): void {
    user.value = null
  }

  return { user, isAdmin, canContribute, fetchMe, login, register, logout, clear }
})
