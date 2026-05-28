# Deploy Guide — AS Skill Live Demo

> 把 [`app.py`](../app.py) 部署到 **Hugging Face Spaces**，得到一个**扫码就能用、有 kill-switch、API key 加密存储**的网页 demo。
>
> 全程约 **15 分钟**。

---

## 为什么选 Hugging Face Spaces

| 需求 | HF Spaces 怎么满足 |
|---|---|
| 访客无需注册/登录 | 公开 URL，直接访问 |
| API key 不能暴露 | Settings → Secrets 加密存储，代码用 `os.environ` 读取 |
| 一键开关下线 | 两层保险：(1) 改 `DEMO_ENABLED=false` 环境变量；(2) Space 设置里 Pause Space 按钮 |
| 国内可访问 | huggingface.co 国内可访问，无需代理（部分校园网例外） |
| 免费 | Free 档 CPU Basic（2 vCPU / 16 GB RAM）够本 demo 用 |
| 监控查询 | Logs 实时可见，能看到访客提了什么问题 |
| 防刷爆 API | 单会话 10 次硬上限 + 每日 USD 5 软上限（可调） |

---

## 准备工作（5 分钟）

### 1. 注册 Hugging Face 账号

打开 https://huggingface.co/join → 用邮箱注册（不需要梯子）。

### 2. 准备 DeepSeek API key

如果还没有：

- 打开 https://platform.deepseek.com → 注册 → 充值（最少 ¥10，够本次 demo 跑几千次）
- 创建 API key，复制保存 `sk-...`

> 💡 DeepSeek V4 Pro / `deepseek-v4-pro` 的定价以 DeepSeek 平台公示为准（V4 Pro 比 `deepseek-chat` 稍贵但回答质量更高）。本 demo 单次回答约 2000 tokens，估算约 **¥0.01-0.02/次**。¥20 余额够展示一整天的访问量。

---

## 部署 Space（10 分钟）

### Step 1：建 Space

1. 打开 https://huggingface.co/new-space
2. 填写：
   - **Owner**：选你自己（`LISI-shaui`）
   - **Space name**：`as-skill-demo`（决定 URL：`huggingface.co/spaces/LISI-shaui/as-skill-demo`）
   - **License**：MIT
   - **Select the Space SDK**：选 **Gradio**
   - **Space hardware**：CPU basic（free 档够用）
   - **Public/Private**：**Public**（要让访客直接进）
3. 点 **Create Space**

### Step 2：把 GitHub 代码同步进 Space

新建的 Space 是个独立 git 仓库。把本项目的关键文件复制过去 —— **最简单**走 GitHub Actions 自动同步，**最直接**手工 git push：

**方式 A：手工 git push（推荐第一次走这个，5 分钟）**

```bash
# 在本机 clone 你的 HF Space
git clone https://huggingface.co/spaces/LISI-shaui/as-skill-demo
cd as-skill-demo

# 把 GitHub 仓库里的关键文件全拷过来
SRC=/path/to/ankylosing-spondylitis-skill   # 改成你的本地路径
cp -r $SRC/app.py .
cp -r $SRC/scripts .
cp -r $SRC/data .
cp -r $SRC/sources .          # 可选，让访客也能看到出处
cp $SRC/requirements-app.txt requirements.txt   # ⚠️ 重命名为 requirements.txt
cp $SRC/LICENSE .

# 在 Space 仓库根目录建一个 README.md（HF 用 YAML frontmatter 配置 Space）
cat > README.md << 'EOF'
---
title: AS Skill Demo
emoji: 🦴
colorFrom: blue
colorTo: indigo
sdk: gradio
sdk_version: 4.36.0
app_file: app.py
pinned: false
license: mit
short_description: 强直性脊柱炎专科问诊智能体 — SHAP+LIME+SPA 三层归因
---

# AS Skill Live Demo

让任意 LLM 在 AS 题上质量 +50%。源代码：https://github.com/LISI-shaui/ankylosing-spondylitis-skill
EOF

# push（HF 第一次会让你登录 — 用 HF 账号密码或 token）
git add .
git commit -m "init: AS Skill demo"
git push
```

push 完毕，HF 会自动开始 build（看 Space 页面的 "Building" 状态）。**首次 build 大概 3-5 分钟**（装 gradio + openai + jieba）。

**方式 B：GitHub Actions 自动同步（推荐长期用，10 分钟设置）**

部署完成后再设。在 GitHub 仓库 Settings → Secrets 加 `HF_TOKEN`（HF 设置里建 write token），然后用 [HF 官方 GitHub Action](https://huggingface.co/docs/hub/spaces-github-actions) 自动同步。每次 GitHub push 自动 → HF。

### Step 3：配置 Secrets 和环境变量

到 Space 页面 → **Settings** Tab → 找 **Variables and secrets** 区域：

| 名字 | 类型 | 值 | 说明 |
|---|---|---|---|
| `DEEPSEEK_API_KEY` | **Secret** | `sk-...你的 key` | ⚠️ 一定选 Secret 不选 Variable，否则访客能看见 |
| `DEEPSEEK_MODEL` | Variable | `deepseek-v4-pro` | ⚠️ 请去 [DeepSeek 平台](https://platform.deepseek.com/api-docs/zh-cn/quick_start/pricing) 核对当前可用的精确 model ID；如不可用回退到 `deepseek-chat` 或 `deepseek-reasoner` |
| `DEEPSEEK_BASE_URL` | Variable | `https://api.deepseek.com/v1` | 默认值，不填也行 |
| `DEMO_ENABLED` | Variable | `true` | ⭐ **一键开关**：改成 `false` 立刻下线 |
| `MAX_PER_SESSION` | Variable | `10` | 单会话提问上限 |
| `DAILY_BUDGET_USD` | Variable | `5.0` | 每日预算上限（美元，自动按 token 估算） |

填完会触发 Space 重启，约 30 秒。

### Step 4：验证

打开 `https://huggingface.co/spaces/LISI-shaui/as-skill-demo` —— 应该看到 Gradio 界面：
- 左边输入框 + 示例题
- 右边 6 个 tab（回答 / 意图 / KB / 安全规则 / 三层归因 / system prompt）
- 点示例 "我刚被诊断为强直性脊柱炎..." → 点 "🚀 让 AS Skill 回答" → 等 5-10 秒 → 看到完整回答

如果回答里出现 "未配置 DeepSeek API key"，说明 Secret 没生效 → 回 Step 3 检查名字拼写。

---

## 医创赛展示控制手册

### 展示前 30 分钟
1. 打开 Space 页面，确认状态显示 `Running`（不是 Sleeping）
2. 点一次示例题 → 确认能回答（"暖机"，防止冷启动延迟）
3. 把示例题清空（如果想隐藏），或保留作引导
4. 复制 URL 准备生成 QR

### 展示中
- Space → **Logs** Tab 可以实时看到访客提了什么问题（评委的提问你会一清二楚）
- 同一个评委被限 10 次 / 会话；超了告诉他刷新页面
- 看到 "余额不足" 错误：去 DeepSeek 平台充值

### 展示完
**强烈推荐立刻做一项**：

| 选项 | 怎么做 | 效果 |
|---|---|---|
| 🛑 软关 | Settings → 改 `DEMO_ENABLED=false` | 访客看到"Demo 暂时关闭" |
| ⏸️ 硬关 | Settings 顶部 **Pause Space** 按钮 | 访客看 503 错误页 |
| 🗑️ 退役 | Settings → Delete Space | URL 失效 |

软关最稳：你下次想用直接改回 `true`，30 秒重启就回来。

### 紧急 kill 路径（如果 Space 出问题）
1. 直接把 DeepSeek 的 API key 在 DeepSeek 平台里 revoke / 改成空 → demo 立刻只能展示 Skill 输出，无 LLM 答案，但不会再扣钱
2. HF Space Pause
3. 直接关你电脑（如果你想）

---

## 生成 QR 码（1 分钟）

部署完成、URL 确定后：

```bash
# 在本地跑（一次性）
python scripts/gen_qr.py https://huggingface.co/spaces/LISI-shaui/as-skill-demo
```

生成 `docs/qr-demo.png`。打印或投到 PPT 上即可。

---

## 故障排查

| 现象 | 原因 | 解决 |
|---|---|---|
| Build 失败，红色 ❌ | `requirements.txt` 写错 | Space → Files → 检查 `requirements.txt`，按本指南 Step 2 内容核对 |
| Build 成功但页面打不开 | 没找到 `app.py` 或端口错 | 确认 `app.py` 在仓库根目录；HF 自动用 7860 端口 |
| 回答里始终显示"未配置 API key" | Secret 没生效 | Step 3 重检；Secret 名必须是 `DEEPSEEK_API_KEY`（注意大小写） |
| 回答里说 401 / 403 | API key 过期或没充值 | DeepSeek 平台检查 key 和余额 |
| 回答里说超时 | DeepSeek 偶尔慢 | 重试；若持续，把 `DEEPSEEK_MODEL` 换成 `deepseek-chat`（比 V4 Pro / reasoner 快但质量略低） |
| 报错 model not found | `deepseek-v4-pro` 这个 ID 在你账号里不可用 | 去 DeepSeek 平台看支持的 model ID，把 `DEEPSEEK_MODEL` 改成对应名字 |
| 中文乱码 | HF Space 默认 UTF-8，本身不会 | 检查浏览器编码 |
| 国内访问超慢 | 校园网/某些 ISP 限速 | 换 4G/5G 网络或个人热点；展示时备份截屏 |

---

## 成本预估

| 项 | 单价 | 100 次提问 | 1000 次提问 |
|---|---|---|---|
| DeepSeek API（input 1500 + output 500 token 估） | ≈ ¥0.005/次 | ¥0.5 | ¥5 |
| HF Spaces 托管 | 免费 | 免费 | 免费 |
| **合计** | — | **¥0.5** | **¥5** |

医创赛展示一天 200-500 次提问的话，DeepSeek 花费 ¥1-2.5。¥10 余额够用。

---

## 备选方案

如果不想用 HF Spaces，也可以：
- **Streamlit Community Cloud**：share.streamlit.io，需要重写 `app.py` 为 Streamlit 风格
- **Vercel Python Function**：serverless，技术门槛高一些
- **自有服务器**：阿里云轻量 ¥30/月，能自定义域名

但对**医创赛短期展示**这个场景，HF Spaces 是最快+最便宜+最安全的组合。
