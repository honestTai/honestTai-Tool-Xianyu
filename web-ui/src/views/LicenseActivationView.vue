<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import LocaleToggle from '@/components/layout/LocaleToggle.vue'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { activateLicense, getLicenseStatus } from '@/api/license'

const router = useRouter()
const route = useRoute()

const serverUrl = ref('')
const licenseKey = ref('')
const isLoading = ref(false)
const error = ref('')
const statusMessage = ref('')

onMounted(async () => {
  try {
    const status = await getLicenseStatus()
    serverUrl.value = status.serverUrl || ''
    statusMessage.value = status.message || ''
    if (!status.enabled || status.authorized) {
      router.replace((route.query.redirect as string) || '/login')
    }
  } catch {
    statusMessage.value = '无法读取授权状态'
  }
})

async function handleActivate() {
  if (!licenseKey.value.trim()) {
    error.value = '请输入授权码'
    return
  }

  isLoading.value = true
  error.value = ''

  try {
    await activateLicense({
      licenseKey: licenseKey.value.trim(),
      serverUrl: serverUrl.value.trim() || undefined,
    })
    router.replace((route.query.redirect as string) || '/login')
  } catch (e) {
    error.value = e instanceof Error ? e.message : '授权激活失败'
  } finally {
    isLoading.value = false
  }
}
</script>

<template>
  <div class="relative flex min-h-screen items-center justify-center overflow-hidden bg-slate-100 px-4">
    <div aria-hidden="true" class="absolute inset-0">
      <div class="absolute left-[-10%] top-[-10%] h-72 w-72 rounded-full bg-primary/10 blur-3xl"></div>
      <div class="absolute bottom-[-10%] right-[-5%] h-72 w-72 rounded-full bg-blue-300/10 blur-3xl"></div>
    </div>
    <div class="absolute right-6 top-6">
      <LocaleToggle />
    </div>
    <Card class="app-surface relative z-10 w-full max-w-md border-none">
      <CardHeader>
        <CardTitle class="text-center text-2xl">软件授权</CardTitle>
        <CardDescription class="text-center">
          {{ statusMessage || '请输入授权信息后继续使用' }}
        </CardDescription>
      </CardHeader>
      <form @submit.prevent="handleActivate">
        <CardContent class="grid gap-4">
          <div class="grid gap-2">
            <Label for="license-server">授权服务器</Label>
            <Input
              id="license-server"
              v-model="serverUrl"
              type="url"
              placeholder="https://license.example.com"
            />
          </div>
          <div class="grid gap-2">
            <Label for="license-key">授权码</Label>
            <Input id="license-key" v-model="licenseKey" autocomplete="off" required />
          </div>
          <div v-if="error" class="text-sm font-medium text-red-500" role="alert">
            {{ error }}
          </div>
        </CardContent>
        <CardFooter>
          <Button class="w-full" type="submit" :disabled="isLoading">
            {{ isLoading ? '正在激活...' : '激活授权' }}
          </Button>
        </CardFooter>
      </form>
    </Card>
  </div>
</template>
