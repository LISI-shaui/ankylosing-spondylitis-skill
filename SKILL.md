---
name: ankylosing-spondylitis-agent
description: |
  Generate evidence-grounded, audience-adapted answers to questions about
  Ankylosing Spondylitis (AS / 强直性脊柱炎). Combines a 67-entry clinical
  knowledge base, 47 quality rules, 134 reviewer insights, and three-layer
  attribution (SHAP/LIME/SPA) to produce expert-level responses for both
  patients and physicians.

  USE WHEN: the user mentions ankylosing spondylitis / AS / 强直性脊柱炎 /
  axSpA / spondyloarthritis / 骶髂关节炎 / 中轴脊柱关节炎; asks about AS
  symptoms, diagnosis, treatment, complications, medications (NSAIDs, TNFi,
  IL-17i, JAKi), lifestyle, pregnancy, surgery, or related rheumatology topics
  in the AS scope.

  DO NOT USE FOR: rheumatoid arthritis, lupus, gout, or non-AS rheumatic
  conditions (their KBs are separate).

triggers:
  - "强直性脊柱炎"
  - "AS"
  - "axSpA"
  - "ankylosing spondylitis"
  - "spondyloarthritis"
  - "骶髂关节"
  - "中轴脊柱关节炎"
  - "HLA-B27"

required_files:
  - data/clinical_kb.json
  - data/quality_rules.json
  - data/reviewer_insights.json
  - data/qa_templates.json
  - data/attribution_evidence.json

scripts:
  primary: scripts/answer.py
  helpers:
    - scripts/intent_recognition.py
    - scripts/retrieval.py
    - scripts/prompt_builder.py
---

# AS Skill — 强直性脊柱炎专科问诊智能体

## 核心能力

| 能力 | 实现 | 调用入口 |
|------|------|----------|
| 意图识别 | A-J 模块 × a-d 维度 × 患者/医生受众分类 | `scripts/intent_recognition.py` |
| 检索 | TF-IDF + 分类硬过滤（无 BERT / 无 GPU） | `scripts/retrieval.py` |
| 三层归因注入 | SHAP 模型来源 · LIME 关键短语 · SPA 核心术语 | `data/attribution_evidence.json` |
| 安全闸门 | 47 条质控规则触发拒答 / 转诊 / 警示 | `data/quality_rules.json` |
| 受众适配 | 患者：粗白话+比喻+具体动作；医生：循证+表格+剂量 | 自动切换 |
| 引用规范 | 每条建议附 KB 出处编号；触发真实文献时附 PMID/DOI | 内置 |

## 三步用法

### 方式 1：作为 Claude / GPT / 国产 LLM 的 Skill（推荐）

把整个 `ankylosing-spondylitis-skill/` 目录上传到对话或挂载为本地路径，然后正常提问：

> "AS 患者怀孕了能继续用阿达木单抗吗？"

LLM 会自动：
1. 触发关键词匹配 → 激活 Skill
2. 调用 `scripts/answer.py` 检索 + 归因 + 生成 system prompt
3. 用增强后的 prompt 回答，附 KB 出处编号

### 方式 2：作为独立 CLI 工具

```bash
cd ankylosing-spondylitis-skill
pip install -r requirements.txt
python scripts/answer.py "AS 患者吃布洛芬有用吗？" --audience patient
```

输出：JSON 格式，含 `system_prompt`（直接喂给底层 LLM）、`retrieved`（检索到的 KB 条目）、`intent`（识别意图）、`attribution`（三层归因证据）。

### 方式 3：作为 Python 库

```python
from scripts.answer import ASAgent

agent = ASAgent(audience="auto")  # 自动识别受众
out = agent.answer("我刚被诊断 AS，该了解什么？")
print(out["system_prompt"])    # 系统提示词
print(out["retrieved"][:3])    # Top-3 检索条目
```

## 性能（基于 46 题正式评测）

| 指标 | A 原模型（裸 LLM） | C AS Skill（本方案） | 提升 |
|------|-------------------|---------------------|------|
| 总分（Opus 4.7 异源评分，满分 35） | 19.09 | **28.63** | **+50%** |
| D6 引用质量 | 1.00 | 2.70 | +1.70 |
| E2 检索相关性 | 1.00 | 4.78 | +3.78 |
| 意图识别准确率 | 0% | 85% | +85 pp |
| 受众识别准确率 | 0% | 96% | +96 pp |
| Top-3 检索命中率 | 0% | 96% | +96 pp |
| 单题推理成本 | — | ¥0.02 | — |
| 单题响应时延 | — | 3-5 s | — |

统计学：配对 Wilcoxon Holm-corrected p < 1e-8，效应量 r = 0.87（巨大效应）。

## 数据来源声明

- **clinical_kb.json**（67 条临床循证标尺）：基于 ASAS-EULAR 2022, ACR/SPARTAN 2019, 各 AS 共识/指南整理
- **quality_rules.json**（47 条质控规则）：复合自 ASAS 质控建议 + 项目自研
- **reviewer_insights.json**（134 条专家洞察）：3 位风湿免疫科医生盲评提炼
- **qa_templates.json**（46 题答案模板）：经临床医生审定
- **attribution_evidence.json**（三层归因实证）：SHAP/LIME/SPA 在 46 题上的真实输出

## 局限性（**必读**）

- ⚠️ 本 Skill **仅供医学教育与科普参考，不替代专业医生面诊**
- 知识库覆盖 AS 高频问题（10 模块），但不保证覆盖所有罕见亚型
- 未接入 PubMed 实时检索，文献时效性以 2024Q4 为基准
- 三层归因在 deepseek-v4-flash 等中等模型上效果最佳；强模型（GPT-4 / Claude Opus）上预期增益 +5% ~ +15%
- 跨专科平移需重建知识库

## 引用本工作

```bibtex
@misc{as_skill_2026,
  title  = {AS Skill: A Three-Layer Attribution-Based Trustworthy Medical
            Dialogue Framework for Ankylosing Spondylitis},
  year   = {2026},
  note   = {SHAP + LIME + SPA + RAG + 67 clinical KB entries + 47 quality
            rules + 134 reviewer insights}
}
```

## License

MIT (见 `LICENSE` 文件)
