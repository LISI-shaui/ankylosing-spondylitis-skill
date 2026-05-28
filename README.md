# AS Skill — 强直性脊柱炎专科问诊智能体

> **An evidence-grounded, audience-adapted dialogue skill for Ankylosing Spondylitis.**
> 让任何通用大模型在 AS 专科上**答得像医生**——单题 ¥0.02、3-5 秒响应、无需 GPU。

[![tests](../../actions/workflows/test.yml/badge.svg)](../../actions/workflows/test.yml)
[![lint](../../actions/workflows/lint.yml/badge.svg)](../../actions/workflows/lint.yml)
![License](https://img.shields.io/badge/license-MIT-blue)
![Python](https://img.shields.io/badge/python-3.8+-blue)
![Status](https://img.shields.io/badge/status-research-orange)
[![HF Spaces](https://img.shields.io/badge/🤗_Try_Live-Hugging_Face-yellow)](https://huggingface.co/spaces/LISI-shaui/as-skill-demo)

> 📰 **[v1.0.0 Release Notes →](RELEASE.md)**  ·  🚀 **[Live Demo →](https://huggingface.co/spaces/LISI-shaui/as-skill-demo)**  ·  📦 **[部署指南 →](docs/DEPLOY.md)**  ·  🤝 **[贡献指南 →](CONTRIBUTING.md)**

---

## 🚀 在线体验（医创赛展示版）

| 方式 | 链接 |
|---|---|
| 网页 | https://huggingface.co/spaces/LISI-shaui/as-skill-demo |
| 扫码 | ![QR](docs/qr-demo.png) |
| 模型 | DeepSeek V4 Pro + AS Skill 三层归因增强 |

> 演示由作者临时开放，**点击网页即用**，单会话最多 10 次提问；展示结束后可能临时关闭。
> 演示后端架构与本仓库 `app.py` 完全一致，源码可审计。
> ⚠️ 演示输出**不构成医疗建议**，仅展示方法学。

---

## 🎯 它解决什么

通用大语言模型（ChatGPT / DeepSeek / Qwen / Grok）回答强直性脊柱炎（AS）问题时存在三大缺陷：

1. **引用规范不及格** — JAMA 引用评分中位 < 50%，几乎没有可追溯的文献依据
2. **可读性超阈值** — SMOG 中位 10-14 级，超过美国医学会（AMA）推荐的患者可读性 Grade 6 阈值
3. **专业建议浮于表面** — 缺少专科诊断规则、安全警示、转诊路径

**本 Skill 通过 RAG + 三层归因（SHAP/LIME/SPA）** 让底层 LLM 在 AS 题上的回答质量在 **46 题正式评测**下从 **19.09 → 28.63（满分 35），相对 +50%**，配对 Wilcoxon Holm-corrected `p < 1e-8`，effect size **r = 0.87（统计学巨大效应）**。

---

## ✨ 核心特性

| 特性 | 实现 |
|------|------|
| **意图识别** | A-J 模块 × a-d 维度 × patient/physician 受众分类（关键词+启发规则，无 LLM 调用） |
| **检索增强** | TF-IDF + 分类硬过滤（无 BERT / 无 GPU） |
| **三层归因注入** | SHAP 模型来源 · LIME 关键短语 · SPA 核心术语 — 真实数据来自 46 题归因分析 |
| **安全闸门** | 47 条质控规则（顺势疗法/JAKi 黑框/孕期用药/活疫苗等触发拒答或警示） |
| **受众适配** | 患者：粗白话+比喻+具体动作；医生：循证+剂量+转诊路径 |
| **引用规范** | 每条 KB 条目附真实文献出处（PMID/DOI/期刊年份） |
| **可解释** | 输出包含 intent / retrieved_kb / triggered_rules / attribution_evidence |

---

## 📦 安装

```bash
git clone https://github.com/LISI-shaui/ankylosing-spondylitis-skill.git
cd ankylosing-spondylitis-skill
pip install -r requirements.txt
```

依赖**只有 jieba**（中文分词），无 PyTorch / 无 BERT / 无 FAISS。

跑网页 demo：

```bash
pip install -r requirements-app.txt
export DEEPSEEK_API_KEY=sk-...
python app.py        # 浏览器打开 http://localhost:7860
```

---

## 🚀 三种用法

### 1️⃣ 作为 Claude / GPT / 国产 LLM 的 Skill（推荐）

把整个 `ankylosing-spondylitis-skill/` 目录挂载或上传到对话工具。LLM 检测到用户提问含 AS 关键词（"强直性脊柱炎" / "axSpA" / "HLA-B27" 等）后会自动激活 Skill，把检索结果与归因证据注入它自己的 system prompt。

> 用户："AS 患者怀孕了能继续用阿达木单抗吗？"
>
> LLM 自动：
> 1. 调用 `scripts/answer.py "..." --audience physician`
> 2. 获取 system_prompt（含 KB + 质控 + 归因）
> 3. 用增强后的 prompt 回答，附 KB 出处编号

### 2️⃣ 作为独立 CLI

```bash
# 单题模式
python scripts/answer.py "AS 患者吃布洛芬有用吗？" --audience patient

# 输出仅 system prompt（可直接喂给底层 LLM）
python scripts/answer.py "我刚被诊断 AS" --format prompt

# 交互式模式
python scripts/answer.py --interactive
```

### 3️⃣ 作为 Python 库

```python
import sys
sys.path.insert(0, "ankylosing-spondylitis-skill/scripts")
from answer import ASAgent

# 创建 agent
agent = ASAgent(top_k_kb=5, audience="auto")

# 输入问题，获取增强 prompt
out = agent.answer("我刚被诊断 AS，该了解什么？")

print(out["intent"])               # {'module': 'B', 'audience': 'patient', ...}
print(out["retrieved_kb"][:2])     # Top-2 KB 条目（含真实文献来源）
print(out["triggered_rules"])      # 触发的质控规则
print(out["attribution_summary"])  # 三层归因证据
print(out["system_prompt"])        # 完整 system prompt，可直接喂给底层 LLM

# 结合任意底层 LLM
import openai  # 或 anthropic / deepseek 等
response = openai.ChatCompletion.create(
    model="gpt-4o-mini",
    messages=[
        {"role": "system", "content": out["system_prompt"]},
        {"role": "user", "content": "我刚被诊断 AS，该了解什么？"},
    ],
)
```

---

## 📊 性能（基于 46 题正式评测）

由 **Claude Opus 4.7 异源裁判**直接通读所有 276 份回答逐项评分，3 位风湿免疫科医生盲评作为人工锚定。

| 指标 | A 原模型（裸 LLM） | C AS Skill | 提升 |
|------|-------------------|------------|------|
| 总分（满分 35） | 19.09 | **28.63** | **+50%** |
| D1 准确性 | 3.80 | 4.20 | +0.39 |
| D2 完整性 | 3.61 | 4.15 | +0.54 |
| D3 受众适配 | 3.57 | 4.26 | +0.70 |
| D4 安全性 | 3.07 | 4.11 | +1.04 |
| D5 可操作性 | 3.04 | 4.43 | +1.39 |
| D6 引用质量 | 1.00 | 2.70 | **+1.70** |
| E2 检索相关性 | 1.00 | 4.78 | **+3.78** |
| 意图识别准确率 | 0% | 85% | +85 pp |
| 受众识别准确率 | 0% | 96% | +96 pp |
| Top-3 检索命中率 | 0% | 96% | +96 pp |

**统计学**：Friedman χ²(2) = 80.0, p < 1e-17；Wilcoxon Holm-corrected p < 1e-8；effect size r = 0.87。

### 贡献度分解

- **RAG + 知识库 + SHAP 是根基**：贡献约 **+7.4 分**
- **LIME + SPA 是临门一脚**：贡献约 **+2.2 分**
- **两者缺一不可** — 没有 RAG 答案没出处，没有三层归因答案不精彩

---

## 📚 数据来源

- `data/clinical_kb.json`（67 条临床循证标尺）— ASAS-EULAR 2022, ACR/SPARTAN 2019, 各 AS 共识/指南
- `data/quality_rules.json`（47 条质控规则）— 自研 + ASAS 质控建议
- `data/reviewer_insights.json`（134 条专家洞察）— 3 位风湿免疫科医生盲评提炼
- `data/qa_templates.json`（46 题答案模板）— 经临床医生审定
- `data/attribution_evidence.json`（三层归因实证）— SHAP/LIME/SPA 在 46 题上的真实输出汇总
- `data/intent_codebook.json`（意图码表）— A-J 模块 × a-d 维度 × patient/physician 受众

---

## 🎓 方法学创新

### 三层创新

1. **反向工程的可解释 LLM 调优** — SHAP+LIME+SPA 首次在 AS 专科同时部署，**把"好回答之所以好"拆解到底**注入下一轮 prompt
2. **双重锚定评估** — Claude Opus 4.7 异源裁判 + 3 位风湿免疫科医生盲评，拒绝 AI 评 AI 循环论证
3. **Skill 化部署** — 换 KB 即可切换专科，单题 ¥0.02、无需 GPU、推广任意专科

### 四组件协同

| 组件 | 解决什么问题 | 维度获益 |
|------|------------|----------|
| ① RAG + 专科知识库 | 答案有没有出处 | D6 引用质量 / E2 检索相关性 |
| ② SHAP | 哪位底层 LLM 最会答 | D3 受众适配（医生→DeepSeek 65% / 患者→Kimi 43%）|
| ③ LIME | 金句长什么样 | D4 安全性 / D5 可操作性 |
| ④ SPA | 专业词不能丢 | D1 准确性 / D2 完整性 |

---

## ⚠️ 局限性（必读）

- **仅供医学教育与科普参考，不替代专业医生面诊**
- 知识库覆盖 AS 高频问题（10 模块），未必涵盖所有罕见亚型
- 未接入 PubMed 实时检索，文献时效性以 2024 Q4 为基准
- 在 **DeepSeek-flash 等中等模型上效果最佳**（+50%）；在强模型（GPT-4 / Claude Opus）上预期增益 +5%–15%
- 跨专科平移需重建知识库

---

## 🔧 自定义与扩展

### 切换专科：把 AS 替换成 RA / 银屑病关节炎

1. 替换 `data/clinical_kb.json` 为目标疾病 KB（保持 schema 一致）
2. 替换 `data/quality_rules.json` 为目标疾病质控规则
3. 重跑 SHAP/LIME/SPA 归因分析后替换 `data/attribution_evidence.json`
4. 改 `scripts/intent_recognition.py` 中的关键词词典
5. 改 `SKILL.md` 的 description / triggers

### 接入实时文献检索（PubMed）

在 `scripts/answer.py` 的 `_trigger_rules` 后加一步：

```python
from scripts.pubmed import search_pubmed
recent_papers = search_pubmed(intent["module_name"] + " ankylosing spondylitis",
                              limit=3, year_min=2023)
# 加入 retrieved_kb 一起注入 prompt
```

---

## 📂 目录结构

```
ankylosing-spondylitis-skill/
├── SKILL.md              # 核心入口（声明触发条件、用法）
├── README.md             # 本文件
├── LICENSE
├── requirements.txt
├── .gitignore
├── data/                 # 知识库（618 KB）
│   ├── clinical_kb.json
│   ├── quality_rules.json
│   ├── reviewer_insights.json
│   ├── qa_templates.json
│   ├── attribution_evidence.json
│   └── intent_codebook.json
├── scripts/              # 核心代码
│   ├── answer.py             # 主入口（CLI + Python lib）
│   ├── intent_recognition.py # 意图识别
│   ├── retrieval.py          # TF-IDF 检索器
│   ├── prompt_builder.py     # system prompt 组装
│   └── _prepare_data.py      # 数据准备（仅打包时用，已 gitignore）
├── examples/             # 使用示例
│   └── quick_start.py
└── tests/
    └── test_basic.py
```

---

## 📝 引用

```bibtex
@misc{as_skill_2026,
  title  = {AS Skill: A Three-Layer Attribution-Based Trustworthy Medical
            Dialogue Framework for Ankylosing Spondylitis},
  year   = {2026},
  note   = {SHAP + LIME + SPA + RAG + 67 clinical KB entries + 47 quality
            rules + 134 reviewer insights}
}
```

---

## 📄 License

MIT (见 [LICENSE](LICENSE))

---

## 🙏 致谢

- 知识库构建过程中所有付出
- ASAS-EULAR / ACR/SPARTAN 等国际指南制定者
- Anthropic Claude Opus 4.7 异源裁判
- 3 位风湿免疫科医生独立盲评

---

**🌟 如果这个 Skill 帮到了你，欢迎 Star + 提 Issue + 贡献新的专科知识库！**
