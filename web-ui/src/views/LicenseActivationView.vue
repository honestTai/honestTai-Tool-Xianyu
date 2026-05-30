<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import LocaleToggle from '@/components/layout/LocaleToggle.vue'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { activateLicense, getLicenseStatus } from '@/api/license'
import { ArrowRight, KeyRound, ShieldCheck, X } from 'lucide-vue-next'

const route = useRoute()

const licenseKey = ref('')
const isLoading = ref(false)
const error = ref('')
const statusMessage = ref('')
const appIconUrl = '/app-assets/app-icon.png'

onMounted(async () => {
  try {
    const status = await getLicenseStatus()
    statusMessage.value = status.message || ''
    if (!status.enabled || status.authorized) {
      redirectToTarget()
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
    const status = await activateLicense({
      licenseKey: licenseKey.value.trim(),
    })
    if (!status.enabled || status.authorized) {
      redirectToTarget()
      return
    }
    statusMessage.value = status.message || ''
    error.value = '授权状态未生效，请稍后重试'
  } catch (e) {
    error.value = e instanceof Error ? e.message : '授权激活失败'
  } finally {
    isLoading.value = false
  }
}

function handleCancel() {
  licenseKey.value = ''
  error.value = ''
}

function redirectToTarget() {
  const rawRedirect = Array.isArray(route.query.redirect)
    ? route.query.redirect[0]
    : route.query.redirect
  const target = typeof rawRedirect === 'string' && rawRedirect.startsWith('/') && !rawRedirect.startsWith('//')
    ? rawRedirect
    : '/dashboard'
  window.location.replace(target)
}
</script>

<template>
  <div class="relative flex min-h-screen items-center justify-center overflow-hidden bg-background px-4 py-10">
    <div class="absolute right-6 top-6 z-20">
      <LocaleToggle />
    </div>

    <div class="relative z-10 grid w-full max-w-5xl overflow-hidden rounded-3xl border border-slate-200/70 bg-white shadow-xl shadow-slate-200/60 md:grid-cols-[0.92fr_1.08fr]">
      <aside class="relative hidden min-h-[520px] flex-col justify-between bg-slate-950 p-8 text-white md:flex">
        <div class="absolute inset-0 bg-[radial-gradient(circle_at_20%_20%,rgba(59,130,246,0.42),transparent_30%),linear-gradient(145deg,rgba(15,23,42,0.98),rgba(30,64,175,0.86))]"></div>
        <div class="relative">
          <div class="flex items-center gap-3">
            <img :src="appIconUrl" alt="" class="h-9 w-9 rounded-lg shadow-lg shadow-blue-950/40" />
            <div>
              <p class="text-sm font-semibold text-white/70">honestTai</p>
              <h1 class="text-2xl font-black leading-tight">闲鱼客户端</h1>
            </div>
          </div>
          <div class="mt-16 space-y-4">
            <div class="inline-flex h-12 w-12 items-center justify-center rounded-2xl bg-white/12 ring-1 ring-white/20">
              <ShieldCheck class="h-6 w-6 text-blue-100" />
            </div>
            <div>
              <h2 class="text-3xl font-black tracking-tight">软件授权</h2>
              <p class="mt-3 max-w-xs text-sm leading-6 text-blue-100/80">
                {{ statusMessage || '请输入授权码后继续使用' }}
              </p>
            </div>
          </div>
        </div>

        <div class="relative rounded-2xl border border-white/10 bg-white/10 p-4 backdrop-blur">
          <div class="flex items-center gap-3">
            <span class="h-2.5 w-2.5 rounded-full bg-amber-300 shadow-[0_0_12px_rgba(252,211,77,0.75)]"></span>
            <span class="text-sm font-semibold text-white/85">等待激活授权</span>
          </div>
        </div>
      </aside>

      <main class="flex min-h-[520px] items-center justify-center bg-white p-6 sm:p-10">
        <Card class="w-full max-w-md border-none bg-transparent shadow-none">
          <CardHeader class="px-0 pb-6">
            <div class="mb-5 flex items-center gap-3 md:hidden">
              <img :src="appIconUrl" alt="" class="h-10 w-10 rounded-xl" />
              <div>
                <p class="text-xs font-semibold text-slate-400">honestTai</p>
                <p class="text-base font-black text-slate-800">闲鱼客户端</p>
              </div>
            </div>
            <div class="mb-4 inline-flex h-11 w-11 items-center justify-center rounded-2xl bg-primary/10 text-primary">
              <KeyRound class="h-5 w-5" />
            </div>
            <CardTitle class="text-3xl font-black tracking-tight text-slate-900">输入授权码</CardTitle>
            <CardDescription class="pt-2 text-base text-slate-500">
              用授权码激活后即可进入客户端。
            </CardDescription>
          </CardHeader>

          <form @submit.prevent="handleActivate">
            <CardContent class="grid gap-5 px-0">
              <div class="grid gap-2">
                <Label for="license-key" class="flex items-center gap-2 text-sm font-bold text-slate-700">
                  <KeyRound class="h-4 w-4 text-slate-400" />
                  授权码
                </Label>
                <Input
                  id="license-key"
                  v-model="licenseKey"
                  autocomplete="off"
                  required
                  autofocus
                  placeholder="请输入授权码"
                  class="h-12 rounded-xl bg-slate-50 text-base"
                />
              </div>

              <div v-if="error" class="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm font-medium text-rose-700" role="alert">
                {{ error }}
              </div>

              <div class="flex flex-col-reverse gap-3 pt-2 sm:flex-row">
                <Button
                  type="button"
                  variant="outline"
                  class="h-12 flex-1 rounded-xl"
                  @click="handleCancel"
                >
                  <X class="mr-2 h-4 w-4" />
                  清空
                </Button>
                <Button
                  type="submit"
                  class="h-12 flex-1 rounded-xl shadow-md shadow-primary/20"
                  :disabled="isLoading"
                >
                  {{ isLoading ? '正在激活...' : '激活授权' }}
                  <ArrowRight class="ml-2 h-4 w-4" />
                </Button>
              </div>
            </CardContent>
          </form>
        </Card>
      </main>
    </div>
  </div>
</template>

<style scoped>
@media (max-width: 767px) {
  :deep(.rounded-3xl) {
    border-radius: 1.25rem;
  }
}
</style>
