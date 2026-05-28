# 客户端授权接入说明

本仓库只包含客户 exe 运行必须携带的最小授权校验代码。完整授权服务和 Tauri 管理端放在独立目录：

```text
C:\Users\hones\Desktop\project\honestTai-License
```

## 运行时行为

- PyInstaller exe 启动时会先校验授权，未激活时弹出授权码输入窗口。
- `--run-spider` 子进程会复用同一份授权缓存，未授权时不会执行爬虫。
- FastAPI 会保护 `/api/*` 业务接口和 `/auth/status` 登录接口；`/api/license/status` 和 `/api/license/activate` 放行。
- WebSocket `/ws` 在未授权时会拒绝连接，避免未授权页面继续接收运行状态推送。
- 运行中心跳失败后会停止调度器和正在运行的任务，新 API 请求会返回 403。

## 配置

```env
LICENSE_ENFORCEMENT_ENABLED=true
LICENSE_SERVER_URL=https://license.example.com
LICENSE_CLIENT_SECRET=honesttai-xianyu-license-client-v1
```

源码开发时默认不启用授权；打包 exe 中默认启用授权。需要在源码模式强制测试授权时，显式设置 `LICENSE_ENFORCEMENT_ENABLED=true`。

本地授权缓存写入 exe 同目录：

```text
state/license.dat
```

该文件只保存激活状态和服务端返回摘要，不作为最终授权依据；启动和心跳仍必须联网访问授权服务。
