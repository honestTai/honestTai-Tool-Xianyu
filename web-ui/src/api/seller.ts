import { http } from '@/lib/http'

export interface SellerAccount {
  name: string
  path: string
}

export interface SellerChat {
  session_id: string
  peer_nick: string
  peer_user_id: string
  unread: number
  last_msg: string
  ts: number
  session_type: number
  item_id?: string
  source: string
}

export interface SellerMessage {
  send_user_id: string
  send_user_name: string
  message: unknown
}

export interface PublishItemPayload {
  account_name?: string | null
  title: string
  desc: string
  images: string[]
  price: number
  original_price?: number | null
  delivery: '包邮' | '按距离计费' | '一口价' | '无需邮寄'
  post_price: number
  can_self_pickup: boolean
}

export async function getSellerAccounts(): Promise<{ accounts: SellerAccount[] }> {
  return await http('/api/seller/accounts')
}

export async function getSellerAuthStatus(accountName?: string | null): Promise<Record<string, unknown>> {
  return await http('/api/seller/auth/status', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ account_name: accountName || null }),
  })
}

export async function listSellerChats(payload: {
  account_name?: string | null
  fetch_num?: number
  watch_secs?: number
}): Promise<{ sessions: SellerChat[]; total: number; has_more: boolean }> {
  return await http('/api/seller/chats', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}

export async function getSellerChatHistory(payload: {
  account_name?: string | null
  cid: string
  limit_per_page?: number
}): Promise<{ messages: SellerMessage[] }> {
  return await http('/api/seller/history', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}

export async function sendSellerMessage(payload: {
  account_name?: string | null
  cid: string
  toid: string
  text: string
  item_id?: string
}): Promise<Record<string, unknown>> {
  return await http('/api/seller/send', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}

export async function publishSellerItem(payload: PublishItemPayload): Promise<Record<string, unknown>> {
  return await http('/api/seller/publish', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}
