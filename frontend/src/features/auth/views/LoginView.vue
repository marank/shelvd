<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Spinner } from '@/components/ui/spinner'
import { useAuthStore } from '@/stores/auth'
import SourceLink from '@/components/app/SourceLink.vue'

const props = defineProps<{ mode?: 'login' | 'register' }>()

const { t } = useI18n()
const auth = useAuthStore()
const route = useRoute()
const router = useRouter()

const username = ref('')
const password = ref('')
const email = ref('')
const error = ref('')
const busy = ref(false)

async function submit() {
  error.value = ''
  busy.value = true
  try {
    if (props.mode === 'register') await auth.register(username.value, password.value, email.value)
    else await auth.login(username.value, password.value)
    const next = typeof route.query.next === 'string' && route.query.next.startsWith('/')
    await router.replace(next ? String(route.query.next) : { name: 'home' })
  } catch (e) {
    error.value = e instanceof Error ? e.message : t('errors.generic')
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <Card>
    <CardHeader>
      <CardTitle>{{
        mode === 'register' ? t('auth.registerTitle') : t('auth.loginTitle')
      }}</CardTitle>
      <CardDescription>
        {{ mode === 'register' ? t('auth.registerHint') : t('auth.loginHint') }}
      </CardDescription>
    </CardHeader>
    <CardContent>
      <form class="grid gap-4" @submit.prevent="submit">
        <div class="grid gap-2">
          <Label for="username">{{ t('fields.username') }}</Label>
          <!-- eslint-disable-next-line vuejs-accessibility/no-autofocus -- signing in is the only thing this page is for -->
          <Input id="username" v-model="username" autocomplete="username" required autofocus />
        </div>
        <div v-if="mode === 'register'" class="grid gap-2">
          <Label for="email">
            {{ t('fields.email') }}
            <span class="text-muted-foreground">({{ t('common.optional') }})</span>
          </Label>
          <Input id="email" v-model="email" type="email" autocomplete="email" />
        </div>
        <div class="grid gap-2">
          <Label for="password">{{ t('fields.password') }}</Label>
          <Input
            id="password"
            v-model="password"
            type="password"
            :autocomplete="mode === 'register' ? 'new-password' : 'current-password'"
            required
          />
        </div>
        <Alert v-if="error" variant="destructive">
          <AlertDescription data-testid="auth-error">{{ error }}</AlertDescription>
        </Alert>
        <Button type="submit" :disabled="busy" class="w-full">
          <Spinner v-if="busy" />
          {{ mode === 'register' ? t('auth.register') : t('auth.login') }}
        </Button>
        <p class="text-center text-sm text-muted-foreground">
          <RouterLink
            v-if="mode === 'register'"
            :to="{ name: 'login' }"
            class="underline underline-offset-4 hover:text-foreground"
          >
            {{ t('auth.haveAccount') }}
          </RouterLink>
          <RouterLink
            v-else
            :to="{ name: 'register' }"
            class="underline underline-offset-4 hover:text-foreground"
          >
            {{ t('auth.noAccount') }}
          </RouterLink>
        </p>
      </form>
      <SourceLink class="mt-6" />
    </CardContent>
  </Card>
</template>
