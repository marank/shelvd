<script setup lang="ts">
import { LogOut, Trash2, UserPlus } from '@lucide/vue'
import { useQueryClient } from '@tanstack/vue-query'
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { toast } from 'vue-sonner'
import type { Library, Member } from '@/api/types'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Spinner } from '@/components/ui/spinner'
import { keys } from '@/features/library/composables/queryKeys'
import { useAuthStore } from '@/stores/auth'
import { errorMessage } from '../../composables/format'
import {
  useMemberMutations,
  useMembers,
  type MemberRole,
} from '../../composables/useLibrarySettings'
import ConfirmDialog from '@/components/app/ConfirmDialog.vue'
import NativeSelect from '@/components/app/NativeSelect.vue'

const props = defineProps<{ library: Library; isOwner: boolean }>()
const { t } = useI18n()
const router = useRouter()
const auth = useAuthStore()
const client = useQueryClient()
const libraryId = computed(() => props.library.id)

const members = useMembers(libraryId)
const { add, setRole, remove } = useMemberMutations(libraryId)
const roleOptions = computed(() =>
  (['viewer', 'editor'] as const).map((r) => ({ value: r, label: t(`choices.role.${r}`) })),
)
const me = computed(() => members.data.value?.find((m) => m.username === auth.user?.username))

// Add
const username = ref('')
const role = ref<MemberRole>('viewer')
const addError = ref('')
async function submitAdd() {
  const name = username.value.trim()
  if (!name) return
  addError.value = ''
  try {
    await add.mutateAsync({ username: name, role: role.value })
    toast.success(t('manage.settings.memberAdded', { name }))
    username.value = ''
  } catch (e) {
    addError.value = errorMessage(e, t('errors.generic'))
  }
}

async function changeRole(member: Member, value: string) {
  try {
    await setRole.mutateAsync({ id: member.id, role: value as MemberRole })
    toast.success(t('manage.settings.roleChanged', { name: member.username }))
  } catch (e) {
    toast.error(errorMessage(e, t('errors.generic')))
  }
}

// Remove someone (owner) or leave (anyone else)
const removing = ref<Member | null>(null)
const removeError = ref('')
const removeOpen = computed({
  get: () => !!removing.value,
  set: (value) => {
    if (!value) removing.value = null
  },
})
const leaving = computed(() => !!removing.value && removing.value.id === me.value?.id)
function startRemove(member: Member) {
  removing.value = member
  removeError.value = ''
}
async function confirmRemove() {
  const member = removing.value
  if (!member) return
  const self = leaving.value
  try {
    await remove.mutateAsync(member.id)
    removing.value = null
    if (self) {
      await client.invalidateQueries({ queryKey: keys.libraries })
      toast.success(t('manage.settings.left', { name: props.library.name }))
      await router.push({ name: 'home' })
    } else {
      toast.success(t('manage.settings.memberRemoved', { name: member.username }))
    }
  } catch (e) {
    removeError.value = errorMessage(e, t('errors.generic'))
  }
}
</script>

<template>
  <Card data-testid="settings-members">
    <CardHeader>
      <CardTitle>{{ t('manage.settings.members') }}</CardTitle>
      <CardDescription>{{ t('manage.settings.membersHint') }}</CardDescription>
    </CardHeader>
    <CardContent class="grid gap-4">
      <dl class="grid gap-1 text-sm">
        <div v-for="r in ['viewer', 'editor'] as const" :key="r" class="flex flex-wrap gap-x-2">
          <dt class="font-medium">{{ t(`choices.role.${r}`) }}:</dt>
          <dd class="text-muted-foreground">{{ t(`manage.settings.roleHint.${r}`) }}</dd>
        </div>
      </dl>

      <ul class="divide-y rounded-lg border">
        <li class="flex items-center gap-2 p-2.5 text-sm" data-testid="member-owner">
          <span class="min-w-0 flex-1 truncate font-medium">{{ library.owner }}</span>
          <Badge variant="outline">{{ t('choices.role.owner') }}</Badge>
        </li>
        <li v-if="members.isPending.value" class="flex justify-center p-3">
          <Spinner />
        </li>
        <li
          v-for="member in members.data.value ?? []"
          :key="member.id"
          class="flex flex-wrap items-center gap-2 p-2.5 text-sm"
          data-testid="member-row"
        >
          <span class="min-w-0 flex-1 truncate font-medium">{{ member.username }}</span>
          <template v-if="isOwner">
            <NativeSelect
              :model-value="member.role"
              :options="roleOptions"
              class="w-36"
              :aria-label="t('manage.settings.role')"
              data-testid="member-role"
              @update:model-value="changeRole(member, $event)"
            />
            <Button
              variant="ghost"
              size="icon-sm"
              data-testid="member-remove"
              :aria-label="t('manage.settings.removeMember')"
              @click="startRemove(member)"
            >
              <Trash2 />
            </Button>
          </template>
          <Badge v-else variant="secondary" data-testid="member-role-badge">
            {{ t(`choices.role.${member.role}`) }}
          </Badge>
        </li>
      </ul>

      <form
        v-if="isOwner"
        class="flex flex-wrap items-center gap-2"
        data-testid="member-add"
        @submit.prevent="submitAdd"
      >
        <Input
          v-model="username"
          class="min-w-0 flex-1 basis-40"
          autocomplete="off"
          :placeholder="t('fields.username')"
          :aria-label="t('fields.username')"
          data-testid="member-username"
        />
        <NativeSelect
          v-model="role"
          :options="roleOptions"
          class="w-36"
          :aria-label="t('manage.settings.role')"
          data-testid="member-new-role"
        />
        <Button type="submit" variant="outline" :disabled="!username.trim() || add.isPending.value">
          <UserPlus />
          {{ t('manage.settings.addMember') }}
        </Button>
      </form>
      <Alert v-if="addError" variant="destructive">
        <AlertDescription data-testid="member-error">{{ addError }}</AlertDescription>
      </Alert>

      <div v-if="!isOwner && me">
        <Button variant="destructive" data-testid="leave-library" @click="startRemove(me)">
          <LogOut />
          {{ t('manage.settings.leave') }}
        </Button>
      </div>
    </CardContent>

    <ConfirmDialog
      v-model:open="removeOpen"
      :title="
        leaving
          ? t('manage.settings.leaveTitle', { name: library.name })
          : t('manage.settings.removeTitle', { name: removing?.username ?? '' })
      "
      :description="leaving ? t('manage.settings.leaveHint') : t('manage.settings.removeHint')"
      :confirm-label="leaving ? t('manage.settings.leave') : t('manage.settings.removeMember')"
      :busy="remove.isPending.value"
      :error="removeError"
      @confirm="confirmRemove"
    />
  </Card>
</template>
