# 买家侧扫货 Hook

这个 hook 用于把“推荐商品命中”事件转发给你自己的项目服务。

触发时机：

1. 商品详情已抓取。
2. 卖家信息已合并。
3. AI 或关键词规则已完成判断。
4. 结果已写入 SQLite。
5. `ai_analysis.is_recommended == true`。

默认关闭，不影响原有监控、落库和通知逻辑。

## 配置

在 `.env` 中开启：

```env
BUYER_AGENT_ENABLED=true
BUYER_AGENT_WEBHOOK_URL=http://127.0.0.1:9001/goofish/recommended
BUYER_AGENT_WEBHOOK_HEADERS='{"X-API-TOKEN":"your-secret-token"}'
BUYER_AGENT_WEBHOOK_TIMEOUT_SECONDS=10
```

建议你的服务先做人工确认、频控和黑名单，再决定是否继续联系卖家。

## Payload

hook 会向 `BUYER_AGENT_WEBHOOK_URL` 发送 JSON：

```json
{
  "event": "recommended_item",
  "keyword": "macbook",
  "task_name": "Macbook 扫货",
  "crawl_time": "2026-05-25T12:00:00",
  "item": {
    "id": "123",
    "title": "MacBook Pro",
    "price": "5999",
    "link": "https://www.goofish.com/item?id=123",
    "main_image": "https://img.example.com/a.jpg",
    "image_urls": ["https://img.example.com/a.jpg"],
    "want_count": "8",
    "browse_count": "99"
  },
  "seller": {
    "卖家昵称": "demo"
  },
  "analysis": {
    "is_recommended": true,
    "reason": "价格合适",
    "analysis_source": "ai",
    "keyword_hit_count": 0
  },
  "price_reference": {},
  "price_insight": {},
  "raw_record": {}
}
```

`raw_record` 保留原始中文字段，方便你后续继续扩字段，不需要改 hook 协议。
