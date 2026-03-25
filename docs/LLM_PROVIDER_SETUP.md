# LLM PROVIDER SETUP

## 当前支持
当前 `services/llm/adapter.py` 支持三种模式：

1. `stub`
   - 默认模式
   - 本地开发可直接跑通，不依赖外部模型

2. `openai_compatible`
   - 用于兼容 OpenAI Chat Completions 风格接口的提供商
   - 要求接口支持 `response_format={"type":"json_object"}`

3. `minimaxi`
   - 用于 MiniMax 官方文本对话接口
   - 当前按官方文档调用：`POST /v1/text/chatcompletion_v2`

## 环境变量
### OpenAI Compatible
```env
LLM_PROVIDER=openai_compatible
LLM_MODEL=<your-model>
LLM_BASE_URL=<https://.../v1>
LLM_API_KEY=<your-key>
LLM_TIMEOUT_SECONDS=120
```

### MiniMax 官方接口
```env
LLM_PROVIDER=minimaxi
LLM_MODEL=MiniMax-M2.5
LLM_BASE_URL=https://api.minimaxi.com
LLM_API_KEY=<your-key>
LLM_TIMEOUT_SECONDS=120
```

注意：代码当前支持两种写法：

```text
POST <LLM_BASE_URL>/chat/completions
```

或直接把 `LLM_BASE_URL` 配成完整接口路径：

```text
https://.../chat/completions
```

也就是说，既支持“API 根路径”，也支持“完整 chat/completions 路径”。

## 当前行为
- 如果 provider/base_url/api_key 没配完整，自动回退到 `stub`
- 这样不会破坏现有本地开发链路

## 下一步建议
- 先用真实提供商验证 Extraction
- 验证通过后，再将 Gap / Writing 逐步切到真实模型调用
