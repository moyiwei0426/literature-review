# DEPENDENCIES

## Step 01 基础依赖
- `fastapi`
- `uvicorn`
- `pydantic`
- `pydantic-settings`
- `httpx`

## 安装方式
在项目目录执行：

```bash
python3 -m pip install -r requirements.txt
```

## 当前验证结果
- `scripts/cli.py show-status`：可运行
- `infra/settings.py`：依赖 `pydantic` / `pydantic-settings`
- `api/main.py`：依赖 `fastapi`

因此在继续 Step 02 / Step 03 前，建议先安装基础依赖。
