"""AS Skill — Hugging Face Spaces 网页 Demo（Gradio）

部署指南：见 docs/DEPLOY.md
环境变量（在 HF Space → Settings → Variables and secrets 配置）：
    DEEPSEEK_API_KEY    [Secret]  — DeepSeek API key (sk-...)
    DEEPSEEK_MODEL      [Var]     — 默认 'deepseek-chat'
    DEEPSEEK_BASE_URL   [Var]     — 默认 'https://api.deepseek.com/v1'
    DEMO_ENABLED        [Var]     — 'true'/'false' 一键开关（默认 true）
    MAX_PER_SESSION     [Var]     — 单会话最大提问次数（默认 10）
    DAILY_BUDGET_USD    [Var]     — 单日预算上限（默认 5 美元，防 DeepSeek 余额爆光）

本地运行：
    pip install -r requirements-app.txt
    python app.py
"""
import hashlib
import os
import sys
import time
from pathlib import Path
from threading import Lock

import gradio as gr

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "scripts"))

from answer import ASAgent  # noqa: E402

# ─────────────────────────── 配置 ───────────────────────────
DEMO_ENABLED = os.environ.get("DEMO_ENABLED", "true").lower() == "true"
API_KEY = os.environ.get("DEEPSEEK_API_KEY", "").strip()
MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat").strip()
BASE_URL = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1").strip()
MAX_PER_SESSION = int(os.environ.get("MAX_PER_SESSION", "10"))
DAILY_BUDGET_USD = float(os.environ.get("DAILY_BUDGET_USD", "5.0"))
TITLE = "AS Skill Live Demo — 强直性脊柱炎专科问诊智能体"

# ─────────────────────────── 全局状态 ───────────────────────────
agent = ASAgent(top_k_kb=5, audience="auto")

# 跨会话简易计数（每天重置）。在 HF 多用户共享同一 Space worker。
_global = {
    "day": time.strftime("%Y-%m-%d"),
    "queries_today": 0,
    "tokens_today": 0,        # 粗略 — DeepSeek 计 input + output token
    "blocked": False,         # 触发预算上限后置 True
}
_global_lock = Lock()

# 答案缓存（同问 + 同受众，复用上次 DeepSeek 输出，省钱）
_cache = {}
_cache_lock = Lock()

# DeepSeek 客户端
client = None
if API_KEY:
    try:
        from openai import OpenAI
        client = OpenAI(api_key=API_KEY, base_url=BASE_URL)
    except ImportError:
        print("[warn] openai package not installed; LLM call disabled.")
    except Exception as e:
        print(f"[warn] DeepSeek client init failed: {e}")


# ─────────────────────────── 渲染辅助 ───────────────────────────
def _md_intent(intent: dict) -> str:
    if not intent:
        return "_(none)_"
    rows = [
        ("模块", f"{intent.get('module', '?')} ({intent.get('module_name', '')})"),
        ("维度", f"{intent.get('dimension', '?')} ({intent.get('dimension_name', '')})"),
        ("受众", intent.get("audience", "?")),
    ]
    return "| 字段 | 值 |\n|---|---|\n" + "\n".join(f"| {k} | `{v}` |" for k, v in rows)


def _md_kb(retrieved: list) -> str:
    if not retrieved:
        return "_(no KB retrieved)_"
    parts = []
    for i, e in enumerate(retrieved[:5], 1):
        eid = e.get("id", "?")
        title = e.get("title", "(no title)")
        src = e.get("source", "")
        if isinstance(src, dict):
            src = f"{src.get('title', '')} — {src.get('journal', '')} {src.get('year', '')}"
        grade = e.get("evidence_grade") or e.get("evidence_level") or ""
        system = e.get("system", "western")
        emoji = {"tcm": "🌿", "integrated": "🔗", "western": "💊"}.get(system, "•")
        parts.append(
            f"**{i}. {emoji} `{eid}` — {title}**  \n"
            f"  · 出处：{src or '—'}  \n"
            f"  · 证据等级：`{grade or '—'}`  \n"
        )
    return "\n".join(parts)


def _md_rules(triggered: list) -> str:
    if not triggered:
        return "_(no rule triggered)_"
    parts = []
    for r in triggered[:6]:
        rtype = r.get("type", "rule")
        severity = r.get("severity", "")
        rule_txt = (
            r.get("rule") or r.get("required_action") or
            r.get("correct") or r.get("trigger_condition") or
            r.get("error") or str(r)[:200]
        )
        sev_emoji = {"critical": "🚨", "high": "⚠️", "medium": "ℹ️"}.get(severity, "•")
        parts.append(f"{sev_emoji} **[{rtype}/{severity or 'n/a'}]** {rule_txt}")
    return "\n\n".join(parts)


def _md_attribution(att: dict) -> str:
    if not att:
        return "_(none)_"
    lines = ["**SHAP 主导模型**：" + str(att.get("shap_top") or att.get("shap_summary", "—"))]
    lines.append("**LIME 高频金句词**：" + str(att.get("lime_top") or att.get("lime_summary", "—"))[:300])
    lines.append("**SPA 核心术语**：" + str(att.get("spa_top") or att.get("spa_summary", "—"))[:300])
    return "\n\n".join(lines)


# ─────────────────────────── 主逻辑 ───────────────────────────
def _check_budget():
    """每日预算检查 — 粗略按 1M token = $0.27 (DeepSeek pricing) 估算"""
    with _global_lock:
        today = time.strftime("%Y-%m-%d")
        if _global["day"] != today:
            _global["day"] = today
            _global["queries_today"] = 0
            _global["tokens_today"] = 0
            _global["blocked"] = False
        # 1M tokens ≈ $0.27 (input cache miss). 用上限的一半保险
        cost_usd = _global["tokens_today"] * 0.27 / 1_000_000
        if cost_usd >= DAILY_BUDGET_USD:
            _global["blocked"] = True
        return _global["blocked"], cost_usd


def _call_deepseek(system_prompt: str, question: str) -> tuple[str, int]:
    """返回 (answer_text, tokens_used)"""
    if not client:
        return "_(未配置 DeepSeek API key — 仅展示 Skill 输出。)_", 0
    cache_key = hashlib.md5((question + system_prompt[:200]).encode()).hexdigest()
    with _cache_lock:
        if cache_key in _cache:
            return _cache[cache_key] + "\n\n_(💾 缓存命中，未额外调用 API)_", 0
    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": question},
            ],
            max_tokens=1200,
            temperature=0.3,
            timeout=45,
        )
        text = resp.choices[0].message.content or ""
        usage = resp.usage
        total_tokens = (usage.prompt_tokens + usage.completion_tokens) if usage else 0
        with _cache_lock:
            _cache[cache_key] = text
            # 缓存最多 200 条
            if len(_cache) > 200:
                _cache.pop(next(iter(_cache)))
        return text, total_tokens
    except Exception as e:
        return f"⚠️ DeepSeek 调用失败：`{type(e).__name__}: {str(e)[:200]}`", 0


def handle(question: str, audience: str, session_state: dict):
    """主回调。返回 (answer, intent, kb, rules, attribution, prompt, new_state)"""
    state = session_state or {"count": 0}

    if not DEMO_ENABLED:
        msg = "🚧 **Demo 暂时关闭** —— 维护中或展示结束，请稍后再试或联系作者。"
        return msg, "", "", "", "", "", state

    if not question or not question.strip():
        return "请输入问题。", "", "", "", "", "", state

    if state["count"] >= MAX_PER_SESSION:
        msg = (f"⚠️ 本次会话已达 **{MAX_PER_SESSION} 次提问上限**。"
               f" 刷新页面可重新开始（防滥用机制，保证演示稳定）。")
        return msg, "", "", "", "", "", state

    blocked, cost_usd = _check_budget()
    if blocked:
        msg = (f"💰 今日演示预算已用完（≈${cost_usd:.2f} / ${DAILY_BUDGET_USD}）。"
               " 明天 0:00 自动重置，或联系作者。")
        return msg, "", "", "", "", "", state

    # ─── 跑 Skill ───
    try:
        out = agent.answer(question, audience=audience if audience != "auto" else None)
    except TypeError:
        # 旧版 answer() 可能不接受 audience kwarg
        out = agent.answer(question)
    except Exception as e:
        return f"⚠️ Skill 内部错误：{e}", "", "", "", "", "", state

    intent_md = _md_intent(out.get("intent", {}))
    kb_md = _md_kb(out.get("retrieved_kb", []))
    rules_md = _md_rules(out.get("triggered_rules", []))
    att_md = _md_attribution(out.get("attribution_summary", {}))
    prompt_text = out.get("system_prompt", "")

    # ─── 调 DeepSeek 端到端 ───
    answer_text, tokens = _call_deepseek(prompt_text, question)

    state["count"] += 1
    with _global_lock:
        _global["queries_today"] += 1
        _global["tokens_today"] += tokens

    footer = (f"\n\n---\n_使用次数：{state['count']}/{MAX_PER_SESSION} · "
              f"今日总调用：{_global['queries_today']} · "
              f"模型：{MODEL}_")
    return answer_text + footer, intent_md, kb_md, rules_md, att_md, prompt_text, state


# ─────────────────────────── 示例题 ───────────────────────────
EXAMPLES = [
    ["我刚被诊断为强直性脊柱炎，特别害怕，该怎么办？", "patient"],
    ["AS 患者怀孕了能继续用阿达木单抗吗？", "physician"],
    ["督灸治疗 AS 真的有效吗？", "auto"],
    ["我打算要孩子，能用雷公藤多苷片吗？", "patient"],
    ["顺势疗法能根治我的强直性脊柱炎吗？", "patient"],
    ["AS 患者使用 TNFi 后葡萄膜炎复发率与 IL-17i 对比", "physician"],
    ["AS 合并溃疡性结肠炎，能用司库奇尤单抗吗？", "physician"],
    ["游泳和太极拳哪个更适合 AS 患者？", "patient"],
]

DISCLAIMER = """
> ### ⚠️ 重要提示
> 本演示仅用于**展示 AS Skill 方法学**，所有回答**不构成医疗建议**，不能替代专业医生面诊。
> 若你或家人有强直性脊柱炎相关健康问题，请前往**风湿免疫科**就诊。
"""

HEADER = f"""
# 🦴 {TITLE}

让任意通用 LLM 在强直性脊柱炎（AS）专科题上 **答得像医生** — 单题 ¥0.02，3-5 秒响应，无需 GPU。
基于 46 题正式评测，相对裸 LLM 提升 **+50%**（Wilcoxon p < 1e-8，effect size r = 0.87）。

**架构**：意图识别 + TF-IDF 检索（67 西医 + 17 中西医结合 KB）+ 47 条质控规则 + 三层归因（SHAP/LIME/SPA）→ 生成 system prompt → 喂给 DeepSeek v4

🔗 [GitHub 仓库](https://github.com/LISI-shaui/ankylosing-spondylitis-skill) ·
📄 [v1.0.0 Release Notes](https://github.com/LISI-shaui/ankylosing-spondylitis-skill/blob/main/RELEASE.md)
"""


# ─────────────────────────── UI ───────────────────────────
with gr.Blocks(title=TITLE, theme=gr.themes.Soft()) as demo:
    gr.Markdown(HEADER)
    gr.Markdown(DISCLAIMER)

    session_state = gr.State({"count": 0})

    with gr.Row():
        with gr.Column(scale=2):
            question = gr.Textbox(
                label="🩺 你的问题",
                placeholder="例：AS 患者孕期能用生物制剂吗？",
                lines=3,
            )
            audience = gr.Radio(
                ["auto", "patient", "physician"],
                value="auto",
                label="👥 目标受众",
                info="auto = 自动识别患者/医生语气",
            )
            submit = gr.Button("🚀 让 AS Skill 回答", variant="primary", size="lg")

            gr.Examples(
                examples=EXAMPLES,
                inputs=[question, audience],
                label="💡 试试这些问题",
            )

        with gr.Column(scale=3):
            with gr.Tabs():
                with gr.Tab("💬 LLM 回答"):
                    answer_out = gr.Markdown(
                        value="_(点上面例子或自己提问开始)_",
                    )
                with gr.Tab("🎯 意图识别"):
                    intent_out = gr.Markdown()
                with gr.Tab("📚 检索到的 KB"):
                    kb_out = gr.Markdown()
                with gr.Tab("🛡️ 安全规则"):
                    rules_out = gr.Markdown()
                with gr.Tab("🔬 三层归因"):
                    att_out = gr.Markdown()
                with gr.Tab("📜 完整 system prompt"):
                    prompt_out = gr.Textbox(
                        label="（这是注入到 DeepSeek 的 system prompt）",
                        lines=20,
                        max_lines=50,
                        show_copy_button=True,
                    )

    submit.click(
        handle,
        inputs=[question, audience, session_state],
        outputs=[answer_out, intent_out, kb_out, rules_out, att_out, prompt_out, session_state],
    )

    gr.Markdown(
        "---\n"
        "**Made by [@LISI-shaui](https://github.com/LISI-shaui)** · "
        "MIT License · "
        f"模型：`{MODEL}` · "
        f"Skill 版本：v1.1（含中西医结合 KB）"
    )


if __name__ == "__main__":
    demo.queue(default_concurrency_limit=3).launch(
        server_name="0.0.0.0",
        server_port=int(os.environ.get("PORT", "7860")),
        share=False,
        show_error=True,
    )
