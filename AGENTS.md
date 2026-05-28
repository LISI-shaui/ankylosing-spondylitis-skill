# AGENTS.md

> 这份文件遵循 [agents.md](https://agents.md) 开放标准，给 **OpenAI Codex / GitHub Copilot / Cursor / Aider / Gemini CLI** 等 coding agent 阅读。Claude 用户请同时参考根目录的 `SKILL.md`（Anthropic Skills 协议）。

---

## Project overview

**AS Skill** 是一个把强直性脊柱炎（Ankylosing Spondylitis, AS / axSpA / 强直性脊柱炎）专科知识封装成"任意 LLM 都能调用"的检索 + 归因增强工具包。

- **不是**一个独立的聊天机器人，也不是模型微调权重
- **而是**一个 Python 工具：吃用户问题 → 吐增强后的 system prompt + 检索证据 + 三层归因
- 把这段 system prompt 喂给任何 LLM（GPT-4o / Claude / DeepSeek / Qwen / Gemini），就能让该 LLM 在 AS 题上质量 +50%（46 题正式评测）

**核心组件**：意图识别 + TF-IDF 检索 + 47 条质控规则 + 67 条临床 KB + SHAP/LIME/SPA 三层归因证据注入。无 PyTorch、无 BERT、无 GPU、单题 ¥0.02。

---

## When to invoke this skill

**Agent 接到用户提问时，先做关键词检测。命中以下任意一个触发词，就走 AS Skill；否则按常规处理。**

触发词（中英混合，case-insensitive 匹配）：
```
强直性脊柱炎  AS  axSpA  ankylosing spondylitis  spondyloarthritis
骶髂关节  中轴脊柱关节炎  HLA-B27  脊柱关节病  附着点炎
```

典型场景（必须激活）：
- 用户问 AS 症状、诊断、用药（NSAIDs / TNFi / IL-17i / JAKi）、孕期管理、手术指征、生活方式、随访
- 用户问"我 HLA-B27 阳性是不是要得 AS"之类的鉴别诊断
- 用户用错术语但意图明显（"我得了僵直性脊椎炎" / "我背越来越硬"+ 提到 axSpA）

**不要激活**：
- 类风湿关节炎（RA）、系统性红斑狼疮（SLE）、痛风、银屑病关节炎等其他风湿病 —— 它们 KB 不一样，强行用 AS KB 会回答错
- 通用骨科 / 运动医学问题（"我腰扭了"）—— 走通用医学知识即可

---

## How to invoke

### Option 1 — CLI (一次性问答)

```bash
cd ankylosing-spondylitis-skill
pip install -r requirements.txt   # 仅需 jieba
python scripts/answer.py "AS 患者吃布洛芬有用吗？" --audience patient
```

**参数**：

| 参数 | 取值 | 说明 |
|------|------|------|
| `question` | 字符串（位置参数） | 用户原始问题 |
| `--audience` | `patient` / `physician` / `auto` | 受众；`auto` 自动识别（默认） |
| `--top-k-kb` | int，默认 5 | 检索 KB 条目数 |
| `--top-k-insights` | int，默认 3 | 检索专家洞察数 |
| `--format` | `json` / `prompt` | `json`=完整结构（含证据）；`prompt`=只输出 system prompt |
| `--interactive` | flag | 进入交互模式 |

### Option 2 — Python lib（推荐 agent 集成方式）

```python
import sys
sys.path.insert(0, "ankylosing-spondylitis-skill/scripts")
from answer import ASAgent

agent = ASAgent(audience="auto")          # 实例化一次即可，自动加载所有 KB
out = agent.answer("我刚被诊断 AS，该了解什么？")

# out 是 dict，关键字段：
out["system_prompt"]          # str — 直接喂给底层 LLM 作为 system message
out["intent"]                 # dict — {module, dimension, audience, ...}
out["retrieved_kb"]           # list — Top-k KB 条目，每条含 source/PMID/DOI
out["triggered_rules"]        # list — 命中的质控规则（顺势疗法/JAKi 黑框等）
out["attribution_summary"]    # dict — SHAP/LIME/SPA 三层证据摘要
```

### Option 3 — 喂给 OpenAI / Anthropic SDK

```python
from openai import OpenAI
from answer import ASAgent

client = OpenAI()
agent = ASAgent()
out = agent.answer(user_question)

resp = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
        {"role": "system", "content": out["system_prompt"]},  # ← 增强 prompt 在这
        {"role": "user", "content": user_question},
    ],
)
```

---

## Setup

```bash
# 1. clone
git clone https://github.com/LISI-shaui/ankylosing-spondylitis-skill.git
cd ankylosing-spondylitis-skill

# 2. install (Python ≥ 3.8)
pip install -r requirements.txt

# 3. smoke test
python examples/quick_start.py
```

依赖**只有 `jieba`**（中文分词）。无 PyTorch、无 transformers、无 FAISS、无 GPU。

---

## Testing

```bash
# 回归测试（15 项，必须全过）
python tests/test_basic.py

# Lint（CI 用同样配置）
ruff check scripts/ tests/ examples/ --select E,F,W,B --ignore E501,E402
```

CI 在 `main` 上每次 push 跑 `.github/workflows/test.yml` + `.github/workflows/lint.yml`。提 PR 前请确保本地两者都过。

---

## Project layout

```
ankylosing-spondylitis-skill/
├── SKILL.md              ← Anthropic Skills 协议入口（Claude 用）
├── AGENTS.md             ← 本文件，agents.md 协议入口（Codex/Cursor/Copilot 用）
├── README.md             ← 人类阅读的完整文档
├── RELEASE.md            ← v1.0.0 release notes
├── data/                 ← 知识库（618 KB，全部 JSON，不要手改）
│   ├── clinical_kb.json          # 67 条临床循证标尺
│   ├── quality_rules.json        # 47 条质控规则
│   ├── reviewer_insights.json    # 134 条专家洞察
│   ├── qa_templates.json         # 46 题答案模板
│   ├── attribution_evidence.json # SHAP/LIME/SPA 归因实证
│   └── intent_codebook.json      # 意图码表
├── scripts/              ← 核心代码（agent 主要打交道的地方）
│   ├── answer.py               # 主入口（CLI + ASAgent 类）
│   ├── intent_recognition.py   # 意图识别（关键词+启发规则，无 LLM）
│   ├── retrieval.py            # TF-IDF 检索器
│   └── prompt_builder.py       # system prompt 组装
├── examples/quick_start.py     # 跑通示例
└── tests/test_basic.py          # 15 项回归测试
```

---

## Do NOT do

agent 在这个仓库里**禁止**的操作：

1. ❌ **不要重写 `scripts/answer.py` 的核心逻辑**绕过质控规则 —— `quality_rules.json` 是合规底线（顺势疗法、JAKi 黑框警告、孕期用药、活疫苗等），绕过等于出医疗事故
2. ❌ **不要手改 `data/*.json` 里的临床内容**而不更新 `source` 字段 —— 每条 KB 都对应真实文献（PMID/DOI），无依据的修改会破坏引用可追溯性
3. ❌ **不要把"AS Skill 是医生"或"可替代面诊"写进任何文档/输出**——README 第 172 行明确"仅供医学教育与科普参考，不替代专业医生面诊"
4. ❌ **不要在没跑 `ruff check` 的情况下 commit** —— CI 会卡，徒增 push 来回
5. ❌ **不要 commit `_prepare_data.py` 的输出中间文件** —— 已在 `.gitignore` 里
6. ❌ **不要安装 PyTorch / transformers / BERT** —— 本项目"零 GPU 依赖"是核心卖点，加重型依赖等于改变项目定位

---

## Style notes

- Python：遵循 PEP 8，ruff 规则 `E,F,W,B` 减去 `E501,E402`（即允许长行 + 模块顶 import 之前的代码）
- 中文文档：UTF-8 无 BOM，LF 换行（git 配置已处理 CRLF→LF）
- 知识库 JSON：每条 entry 必须有 `id`、`module`（A-J）、`audience`（patient/physician/both）、`source`（文献来源）
- Commit message：用 [Conventional Commits](https://www.conventionalcommits.org/)（`feat:` / `fix:` / `chore:` / `docs:`）

---

## How to extend

要给本 Skill 加新能力，常见路径：

| 想加什么 | 改哪里 |
|---------|--------|
| 新 KB 条目（新指南、新文献） | `data/clinical_kb.json`（加 entry，填全 `source`） |
| 新质控规则 | `data/quality_rules.json`（加 entry，填 `trigger_condition` + `required_action`） |
| 新意图触发关键词 | `scripts/intent_recognition.py` 里的关键词词典 |
| 接入 PubMed 实时检索 | `scripts/answer.py` 在 `_trigger_rules` 后插一步，见 README 第 192 行 |
| 切换专科（RA / 银屑病关节炎） | 整套替换 `data/*.json`，改 `intent_recognition.py` 词典，改 `SKILL.md` / `AGENTS.md` 的 description 和触发词 |

详细贡献流程见根目录 `CONTRIBUTING.md`。

---

## Performance reference

CI / agent 跑测试时可对照这个表判断是否 regression：

| 指标 | v1.0.0 基线 |
|------|------------|
| `test_basic.py` 通过项 | 15/15 |
| `ruff check` errors | 0 |
| 单题端到端时延（无 LLM 调用） | 50-200 ms |
| 单题端到端时延（含 LLM 调用） | 3-5 s |
| `ASAgent()` 实例化时延（首次冷加载） | ~1 s |

---

## Citations & references

如果 agent 在生成 PR / commit / 文档时需要引用本工作：

```bibtex
@misc{as_skill_2026,
  title  = {AS Skill: A Three-Layer Attribution-Based Trustworthy Medical
            Dialogue Framework for Ankylosing Spondylitis},
  version = {1.0.0},
  year   = {2026},
  url    = {https://github.com/LISI-shaui/ankylosing-spondylitis-skill}
}
```

---

**License**: MIT (见 `LICENSE`)
**Maintainer**: LISI-shaui
**Spec version**: agents.md v1
