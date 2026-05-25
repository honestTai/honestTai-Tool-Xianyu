<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { MessageSquare, RefreshCw, SendHorizontal } from 'lucide-vue-next'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import { toast } from '@/components/ui/toast'
import {
  getSellerAccounts,
  getSellerChatHistory,
  listSellerChats,
  sendSellerMessage,
  type SellerAccount,
  type SellerChat,
  type SellerMessage,
} from '@/api/seller'

const AUTO_ACCOUNT = '__auto__'

const accounts = ref<SellerAccount[]>([])
const selectedAccount = ref(AUTO_ACCOUNT)
const chats = ref<SellerChat[]>([])
const selectedChatId = ref('')
const messages = ref<SellerMessage[]>([])
const replyText = ref('')
const fetchNum = ref(50)
const isLoadingChats = ref(false)
const isLoadingHistory = ref(false)
const isSending = ref(false)

const selectedChat = computed(() => chats.value.find((chat) => chat.session_id === selectedChatId.value) || null)
const accountName = computed(() => selectedAccount.value === AUTO_ACCOUNT ? null : selectedAccount.value)

function formatMessage(message: unknown): string {
  if (message == null) return ''
  if (typeof message === 'string') return message
  try {
    return JSON.stringify(message, null, 2)
  } catch {
    return String(message)
  }
}

function normalizeTimestamp(ts: number): string {
  if (!ts) return '-'
  const value = ts > 10_000_000_000 ? ts : ts * 1000
  return new Date(value).toLocaleString()
}

async function loadAccounts() {
  const res = await getSellerAccounts()
  accounts.value = res.accounts
}

async function loadChats() {
  isLoadingChats.value = true
  try {
    const res = await listSellerChats({
      account_name: accountName.value,
      fetch_num: fetchNum.value,
      watch_secs: 0,
    })
    chats.value = res.sessions || []
    const firstChat = chats.value[0]
    if (!selectedChatId.value && firstChat) {
      selectedChatId.value = firstChat.session_id
      await loadHistory()
    }
  } catch (e) {
    toast({ title: '会话加载失败', description: (e as Error).message, variant: 'destructive' })
  } finally {
    isLoadingChats.value = false
  }
}

async function loadHistory() {
  if (!selectedChatId.value) return
  isLoadingHistory.value = true
  try {
    const res = await getSellerChatHistory({
      account_name: accountName.value,
      cid: selectedChatId.value,
      limit_per_page: 30,
    })
    messages.value = res.messages || []
  } catch (e) {
    toast({ title: '聊天记录加载失败', description: (e as Error).message, variant: 'destructive' })
  } finally {
    isLoadingHistory.value = false
  }
}

async function selectChat(chat: SellerChat) {
  selectedChatId.value = chat.session_id
  await loadHistory()
}

async function sendReply() {
  const chat = selectedChat.value
  if (!chat || !replyText.value.trim()) return
  isSending.value = true
  try {
    await sendSellerMessage({
      account_name: accountName.value,
      cid: chat.session_id,
      toid: chat.peer_user_id,
      text: replyText.value.trim(),
      item_id: chat.item_id || '',
    })
    replyText.value = ''
    toast({ title: '消息已发送' })
    await loadHistory()
  } catch (e) {
    toast({ title: '发送失败', description: (e as Error).message, variant: 'destructive' })
  } finally {
    isSending.value = false
  }
}

onMounted(async () => {
  await loadAccounts()
  await loadChats()
})
</script>

<template>
  <div class="space-y-5">
    <div class="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
      <div>
        <h1 class="text-2xl font-bold text-gray-800">客服工作台</h1>
        <p class="mt-1 text-sm text-slate-500">查看闲鱼会话、拉取聊天记录，并人工确认后发送回复。</p>
      </div>
      <div class="flex flex-col gap-3 sm:flex-row">
        <div class="w-full sm:w-56">
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
        <div class="w-full sm:w-28">
          <Label>数量</Label>
          <Input v-model.number="fetchNum" type="number" min="1" max="200" />
        </div>
        <Button class="mt-1 sm:mt-6" :disabled="isLoadingChats" @click="loadChats">
          <RefreshCw class="mr-2 h-4 w-4" />
          刷新
        </Button>
      </div>
    </div>

    <div class="grid gap-4 lg:grid-cols-[360px_1fr]">
      <Card class="overflow-hidden">
        <CardHeader>
          <CardTitle class="flex items-center gap-2 text-base">
            <MessageSquare class="h-4 w-4" />
            会话列表
          </CardTitle>
          <CardDescription>来自 goofish-cli 的 message list-chats。</CardDescription>
        </CardHeader>
        <CardContent class="space-y-2 max-h-[640px] overflow-y-auto">
          <button
            v-for="chat in chats"
            :key="chat.session_id"
            type="button"
            class="w-full rounded-lg border p-3 text-left transition hover:bg-slate-50"
            :class="chat.session_id === selectedChatId ? 'border-primary bg-primary/5' : 'border-slate-200'"
            @click="selectChat(chat)"
          >
            <div class="flex items-center justify-between gap-3">
              <p class="truncate text-sm font-bold text-slate-800">{{ chat.peer_nick || chat.session_id }}</p>
              <span v-if="chat.unread" class="rounded-full bg-rose-500 px-2 py-0.5 text-xs font-bold text-white">{{ chat.unread }}</span>
            </div>
            <p class="mt-1 truncate text-xs text-slate-500">{{ chat.last_msg || '暂无摘要' }}</p>
            <p class="mt-2 text-[11px] text-slate-400">{{ normalizeTimestamp(chat.ts) }}</p>
          </button>
          <p v-if="!chats.length" class="rounded-lg border border-dashed p-6 text-center text-sm text-slate-400">暂无会话</p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle class="text-base">{{ selectedChat?.peer_nick || selectedChat?.session_id || '请选择会话' }}</CardTitle>
          <CardDescription>
            CID: {{ selectedChat?.session_id || '-' }} · 对方 ID: {{ selectedChat?.peer_user_id || '-' }}
          </CardDescription>
        </CardHeader>
        <CardContent class="space-y-4">
          <div class="min-h-[420px] max-h-[520px] overflow-y-auto rounded-lg border bg-slate-50 p-4">
            <div v-if="isLoadingHistory" class="text-sm text-slate-400">加载聊天记录中...</div>
            <div v-else-if="messages.length" class="space-y-3">
              <div v-for="(message, index) in messages" :key="index" class="rounded-lg bg-white p-3 shadow-sm">
                <p class="mb-1 text-xs font-bold text-slate-500">{{ message.send_user_name || message.send_user_id || '未知用户' }}</p>
                <pre class="whitespace-pre-wrap break-words text-sm text-slate-800">{{ formatMessage(message.message) }}</pre>
              </div>
            </div>
            <div v-else class="text-sm text-slate-400">暂无聊天记录</div>
          </div>

          <div class="space-y-2">
            <Label>回复内容</Label>
            <Textarea v-model="replyText" rows="4" placeholder="输入要发送给买家的内容" />
            <div class="flex justify-end">
              <Button :disabled="!selectedChat || !replyText.trim() || isSending" @click="sendReply">
                <SendHorizontal class="mr-2 h-4 w-4" />
                {{ isSending ? '发送中...' : '发送' }}
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  </div>
</template>
