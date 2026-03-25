# OAuth 接入说明

## 当前支持范围
当前项目已新增一套最小 OAuth 接入层，适用于“先通过 OAuth 拿到 access token，再用 OpenAI-compatible 接口发起请求”的场景。

当前实现包含：
- OAuth 配置读取
- authorize URL 生成
- callback code exchange
- token 持久化存储（SQLite）
- refresh token 自动续期
- LLM adapter 动态读取 OAuth access token

## 环境变量
```env
LLM_PROVIDER=oauth_openai_compatible
LLM_MODEL=<your-model>
LLM_BASE_URL=https://.../v1
LLM_TIMEOUT_SECONDS=120

OAUTH_CLIENT_ID=<client-id>
OAUTH_CLIENT_SECRET=<client-secret>
OAUTH_AUTHORIZE_URL=https://.../oauth/authorize
OAUTH_TOKEN_URL=https://.../oauth/token
OAUTH_REDIRECT_URI=http://localhost:8000/auth/oauth/callback
OAUTH_SCOPE=<scope>
```

## 路由
### 1. 开始授权
`GET /auth/oauth/start`

返回：
- `authorize_url`
- `state`

### 2. OAuth 回调
`GET /auth/oauth/callback?code=...&state=...`

行为：
- 用 code 换 access token / refresh token
- 将 token 保存到 SQLite `oauth_tokens` 类别下

### 3. 手动刷新
`POST /auth/oauth/refresh`

行为：
- 用已存储 refresh token 换新 access token

## 当前状态校验与联调支持
现在已经补入：
- OAuth state 持久化存储（SQLite `oauth_states`）
- state 过期校验
- state 一次性消费
- provider health 检查接口
- state 验证接口

新增接口：
- `GET /auth/oauth/health`
- `GET /auth/oauth/state/validate?state=...`

## 当前限制
- 当前默认 provider 名称固定为 `oauth_openai_compatible`
- 当前适合单提供商、单租户开发验证，不是完整多租户 OAuth 平台实现
- 尚未做真实 OAuth 提供商联调成功案例；当前完成的是联调准备与本地最小校验
