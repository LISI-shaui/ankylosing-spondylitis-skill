#!/usr/bin/env python3
"""把检索到的 KB 条目 + 三层归因证据 + 质控规则 + 受众适配规则
   组装成 system prompt，喂给底层 LLM。
"""
import json
from pathlib import Path  # noqa: F401

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


# === 受众适配语句 ===
AUDIENCE_DIRECTIVES = {
    "patient": (
        "受众：患者。回答须满足：\n"
        "  · 用粗白话，避免生僻医学术语（必要术语后加注音 / 一句解释）\n"
        "  · 至少 1 个生活化比喻（如'免疫保安队认错人'）\n"
        "  · 至少 3 条**具体可执行**的行动（带频次、时长、剂量等数字）\n"
        "  · 戒烟必须独立强调为'独立危险因素'\n"
        "  · 末尾附'本回答仅供健康教育参考，不能替代专业医生面诊'声明"
    ),
    "physician": (
        "受众：临床医生。回答须满足：\n"
        "  · 循证密度高，关键论断附引文（PMID / 指南条目）\n"
        "  · 用标准化量表（BASDAI / ASDAS-CRP / BASFI / BASMI 等）\n"
        "  · 给出剂量、疗程、转诊路径、共病联动警示\n"
        "  · 包含必要的安全红线（黑框警告、禁忌、活动疫苗规避）\n"
        "  · 结构化输出：病史 / 查体 / 辅检 / 治疗 四段式（如适用）"
    ),
}


def _format_kb_entry(entry, idx=None, audience="patient"):
    """格式化一条 KB 条目供注入。按受众选择 professional / patient content。"""
    parts = []
    if idx is not None:
        parts.append(f"【KB-{idx}】")
    title = entry.get("title", "")
    if title:
        parts.append(f"**{title}**")
    # 按受众选择内容
    if audience == "physician":
        content = (entry.get("professional_content") or
                   entry.get("content") or
                   entry.get("patient_content", ""))
    else:
        content = (entry.get("patient_content") or
                   entry.get("content") or
                   entry.get("professional_content", ""))
    if content:
        # 截断过长内容（≤ 300 字）
        if len(content) > 300:
            content = content[:300] + "…"
        parts.append(content)
    src = entry.get("source") or entry.get("source_citation")
    if src:
        parts.append(f"（来源：{src}）")
    return "\n  ".join(parts)


def _format_rule(rule):
    """格式化一条质控规则。兼容 medical_correction / safety_rule / common_mistake /
    quality_template 四种 schema。"""
    typ = rule.get("type", rule.get("category", ""))
    sev = rule.get("severity", "")
    head = f"[{typ}" + (f"/{sev}" if sev else "") + "]"

    # medical_correction: error → correct
    if rule.get("error") and rule.get("correct"):
        s = f"{head} ❌ 错误：{rule['error']}  ✅ 正确：{rule['correct']}"
        if rule.get("reference"):
            s += f"（{rule['reference']}）"
        return s
    # safety_rule / common_mistake / quality_template
    trig = rule.get("trigger_condition") or rule.get("rule") or rule.get("description", "")
    act = rule.get("required_action") or rule.get("action") or rule.get("recommendation", "")
    if trig or act:
        s = head
        if trig:
            s += f" 触发：{trig}"
        if act:
            s += f" → 必须：{act}"
        return s
    # 最后兜底：把整条 rule dump
    return head + " " + json.dumps({k: v for k, v in rule.items()
                                     if k not in ("type", "severity")},
                                    ensure_ascii=False)


def _format_insight(insight):
    """格式化一条 reviewer insight。"""
    typ = insight.get("type", "")
    pat = insight.get("pattern", insight.get("content", ""))
    imp = insight.get("improvement", "")
    s = f"[{typ}] {pat}"
    if imp:
        s += f" → 改进：{imp}"
    return s


def build_system_prompt(question, intent, retrieved_kb, retrieved_rules,
                       retrieved_insights, attribution_evidence):
    """组装最终 system prompt。

    Args:
        question: 用户原始问题
        intent: recognize_intent() 返回的 dict
        retrieved_kb: List[dict] Top-K KB 条目
        retrieved_rules: List[dict] 触发的质控规则
        retrieved_insights: List[dict] 相关专家洞察
        attribution_evidence: dict 三层归因汇总
    """
    audience = intent["audience"]
    audience_directive = AUDIENCE_DIRECTIVES[audience]

    lines = []
    # ---- 1. 角色与目标 ----
    lines.append("你是一位**强直性脊柱炎（AS）专科问诊智能体**。")
    lines.append(
        f"用户的提问识别为：模块「{intent.get('module_name', '')}"
        f"({intent['module']})」· 维度「{intent.get('dimension_name', '')}"
        f"({intent['dimension']})」· 受众「{audience}」。"
    )
    lines.append("")

    # ---- 2. 受众适配规则 ----
    lines.append("=" * 50)
    lines.append("【受众适配规则】（**必须严格遵守**）")
    lines.append(audience_directive)
    lines.append("")

    # ---- 3. 检索到的 KB 标尺 ----
    if retrieved_kb:
        lines.append("=" * 50)
        lines.append("【临床循证依据】（基于 ASAS-EULAR 2022 / ACR-SPARTAN 2019 等）")
        for i, kb in enumerate(retrieved_kb, 1):
            lines.append(_format_kb_entry(kb, i, audience))
            lines.append("")
        lines.append("")

    # ---- 4. 触发的质控规则 ----
    if retrieved_rules:
        lines.append("=" * 50)
        lines.append("【必须遵守的质控规则】（**安全红线**）")
        for r in retrieved_rules:
            lines.append(f"  · {_format_rule(r)}")
        lines.append("")

    # ---- 5. 相关专家洞察 ----
    if retrieved_insights:
        lines.append("=" * 50)
        lines.append("【专家洞察 — 类似题目的高质量模式】")
        for ins in retrieved_insights[:3]:
            lines.append(f"  · {_format_insight(ins)}")
        lines.append("")

    # ---- 6. 三层归因证据（关键创新）----
    if attribution_evidence:
        shap = attribution_evidence.get("shap", {})
        lime = attribution_evidence.get("lime", {})
        spa = attribution_evidence.get("spa", {})
        lines.append("=" * 50)
        lines.append("【三层归因 — 优质回答的可解释证据】")
        # SHAP
        if audience == "physician":
            top_shap = shap.get("physician_top_contributor", {})
        else:
            top_shap = shap.get("patient_top_contributor", {})
        if top_shap:
            top3 = list(top_shap.items())[:3]
            shap_str = " / ".join(f"{m}: {c}" for m, c in top3)
            lines.append(f"  SHAP 主导模型（{audience} 题）：{shap_str}")
        # LIME 关键短语
        top_phrases = lime.get("top_phrases", {})
        if top_phrases:
            top_lime = list(top_phrases.items())[:8]
            lines.append(f"  LIME 高频金句词（应自然融入）：" +
                         "、".join(f"{p}({c})" for p, c in top_lime))
        # SPA 核心术语
        top_terms = spa.get("top_terms", {})
        if top_terms:
            top_spa = list(top_terms.items())[:8]
            lines.append(f"  SPA 核心术语（不可省略）：" +
                         "、".join(f"{t}({c})" for t, c in top_spa))
        lines.append("")

    # ---- 7. 最终回答指令 ----
    lines.append("=" * 50)
    lines.append("【生成指令】")
    lines.append("基于以上所有材料，回答以下问题。**禁止编造文献**——只引用上面 KB 列出的条目编号。**禁止打破质控规则**。")
    lines.append("")
    lines.append(f"问题：{question}")
    lines.append("")
    lines.append("现在给出你的回答：")

    return "\n".join(lines)
