<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { PackagePlus, Rocket } from 'lucide-vue-next'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import { toast } from '@/components/ui/toast'
import { getSellerAccounts, publishSellerItem, type SellerAccount } from '@/api/seller'

const AUTO_ACCOUNT = '__auto__'

const accounts = ref<SellerAccount[]>([])
const selectedAccount = ref(AUTO_ACCOUNT)
const title = ref('')
const desc = ref('')
const price = ref<number | undefined>()
const originalPrice = ref<number | undefined>()
const delivery = ref<'包邮' | '按距离计费' | '一口价' | '无需邮寄'>('无需邮寄')
const postPrice = ref(0)
const canSelfPickup = ref(true)
const imageText = ref('')
const result = ref<Record<string, unknown> | null>(null)
const isPublishing = ref(false)

const imagePaths = computed(() => imageText.value
  .split(/\r?\n/)
  .map((line) => line.trim())
  .filter(Boolean))
const accountName = computed(() => selectedAccount.value === AUTO_ACCOUNT ? null : selectedAccount.value)
const canPublish = computed(() => title.value.trim() && desc.value.trim() && Number(price.value) > 0 && imagePaths.value.length)

async function loadAccounts() {
  const res = await getSellerAccounts()
  accounts.value = res.accounts
}

async function publishItem() {
  if (!canPublish.value || !price.value) return
  isPublishing.value = true
  result.value = null
  try {
    result.value = await publishSellerItem({
      account_name: accountName.value,
      title: title.value.trim(),
      desc: desc.value.trim(),
      images: imagePaths.value,
      price: Number(price.value),
      original_price: originalPrice.value ? Number(originalPrice.value) : null,
      delivery: delivery.value,
      post_price: Number(postPrice.value || 0),
      can_self_pickup: canSelfPickup.value,
    })
    toast({ title: '发布完成' })
  } catch (e) {
    toast({ title: '发布失败', description: (e as Error).message, variant: 'destructive' })
  } finally {
    isPublishing.value = false
  }
}

onMounted(loadAccounts)
</script>

<template>
  <div class="space-y-5">
    <div>
      <h1 class="text-2xl font-bold text-gray-800">商品上架</h1>
      <p class="mt-1 text-sm text-slate-500">调用 goofish-cli 的 item publish 能力，自动上传图片、识别类目并发布。</p>
    </div>

    <div class="grid gap-4 xl:grid-cols-[1fr_360px]">
      <Card>
        <CardHeader>
          <CardTitle class="flex items-center gap-2 text-base">
            <PackagePlus class="h-4 w-4" />
            发布信息
          </CardTitle>
          <CardDescription>写操作建议先小批量测试，避免频繁发布触发风控。</CardDescription>
        </CardHeader>
        <CardContent class="space-y-4">
          <div class="grid gap-4 md:grid-cols-2">
            <div>
              <Label>账号</Label>
              <Select v-model="selectedAccount">
                <SelectTrigger><SelectValue placeholder="选择账号" /></SelectTrigger>
                <SelectContent>
                  <SelectItem :value="AUTO_ACCOUNT">自动读取 goofish-cli 登录态</SelectItem>
                  <SelectItem v-for="account in accounts" :key="account.name" :value="account.name">
                    {{ account.name }}
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>发货方式</Label>
              <Select v-model="delivery">
                <SelectTrigger><SelectValue placeholder="选择发货方式" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="无需邮寄">无需邮寄</SelectItem>
                  <SelectItem value="包邮">包邮</SelectItem>
                  <SelectItem value="按距离计费">按距离计费</SelectItem>
                  <SelectItem value="一口价">一口价</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <div>
            <Label>商品标题</Label>
            <Input v-model="title" maxlength="60" placeholder="例如：MacBook Pro M2 16G 512G 自用闲置" />
          </div>

          <div>
            <Label>商品描述</Label>
            <Textarea v-model="desc" rows="8" placeholder="商品成色、配件、发货方式、售后说明等" />
          </div>

          <div class="grid gap-4 md:grid-cols-3">
            <div>
              <Label>售价</Label>
              <Input v-model.number="price" type="number" min="0" step="0.01" />
            </div>
            <div>
              <Label>原价</Label>
              <Input v-model.number="originalPrice" type="number" min="0" step="0.01" />
            </div>
            <div>
              <Label>邮费</Label>
              <Input v-model.number="postPrice" type="number" min="0" step="0.01" />
            </div>
          </div>

          <div>
            <Label>图片路径</Label>
            <Textarea
              v-model="imageText"
              rows="6"
              placeholder="每行一个本机图片路径，例如 C:\\Users\\hones\\Pictures\\item1.jpg"
            />
            <p class="mt-1 text-xs text-slate-400">当前版本先用本机路径，后续可以继续做拖拽上传。</p>
          </div>

          <label class="flex items-center gap-2 text-sm text-slate-600">
            <input v-model="canSelfPickup" type="checkbox" class="h-4 w-4 rounded border-slate-300" />
            支持自提
          </label>

          <div class="flex justify-end">
            <Button :disabled="!canPublish || isPublishing" @click="publishItem">
              <Rocket class="mr-2 h-4 w-4" />
              {{ isPublishing ? '发布中...' : '确认发布' }}
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle class="text-base">发布结果</CardTitle>
          <CardDescription>成功后会返回 item_id 和类目信息。</CardDescription>
        </CardHeader>
        <CardContent>
          <pre class="min-h-[220px] rounded-lg bg-slate-950 p-4 text-xs text-slate-100 overflow-auto">{{ result ? JSON.stringify(result, null, 2) : '等待发布' }}</pre>
        </CardContent>
      </Card>
    </div>
  </div>
</template>
