#!/usr/bin/env python3
"""AS Skill 快速上手示例

跑法：cd ankylosing-spondylitis-skill && python examples/quick_start.py
"""
import json
import sys
from pathlib import Path

# 让 examples/ 能 import scripts/
SCRIPT_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from answer import ASAgent


def demo_patient_question():
    """演示 1：患者提问 — 受众自动识别为 patient"""
    print("\n" + "=" * 70)
    print("Demo 1：患者刚确诊 AS")
    print("=" * 70)

    agent = ASAgent(top_k_kb=4, top_k_insights=2)
    out = agent.answer("我刚被诊断为强直性脊柱炎，需要了解什么？")

    intent = out["intent"]
    print(f"\n[意图识别]")
    print(f"  模块: {intent['module']} ({intent['module_name']})")
    print(f"  维度: {intent['dimension']} ({intent['dimension_name']})")
    print(f"  受众: {intent['audience']}")
    print(f"  完整 intent_code: {intent['intent_code']}")

    print(f"\n[检索到 {len(out['retrieved_kb'])} 条 KB]")
    for i, kb in enumerate(out["retrieved_kb"][:3], 1):
        print(f"  {i}. 【{kb.get('id', '?')}】{kb.get('title', '?')}")
        if kb.get("source"):
            print(f"     来源: {kb['source'][:80]}")

    print(f"\n[触发 {len(out['triggered_rules'])} 条质控规则]")
    for r in out["triggered_rules"][:3]:
        print(f"  · {r.get('rule', r.get('trigger_condition', ''))[:100]}")

    print(f"\n[三层归因证据摘要]")
    a = out["attribution_summary"]
    print(f"  SHAP 主导（{intent['audience']} 题）: {a['shap_top']}")
    print(f"  LIME 高频金句词: {list(a['lime_top_phrases'].keys())[:5]}")
    print(f"  SPA 核心术语: {list(a['spa_top_terms'].keys())[:5]}")

    print(f"\n[完整 system prompt 长度: {len(out['system_prompt'])} 字]")
    print(f"  前 300 字预览:")
    print("  " + out["system_prompt"][:300].replace("\n", "\n  ") + "...")


def demo_physician_question():
    """演示 2：医生提问 — 自动识别为 physician + 专业内容"""
    print("\n" + "=" * 70)
    print("Demo 2：医生 PICO 循证决策题")
    print("=" * 70)

    agent = ASAgent(top_k_kb=3, audience="physician")
    out = agent.answer(
        "合并葡萄膜炎反复发作的 AS 患者，单抗类 TNFi（阿达木单抗）"
        "是否优于受体型 TNFi（依那西普）？")

    intent = out["intent"]
    print(f"\n[意图识别] 模块={intent['module']} 维度={intent['dimension']} 受众={intent['audience']}")
    print(f"\n[检索到 {len(out['retrieved_kb'])} 条 KB]:")
    for i, kb in enumerate(out["retrieved_kb"][:3], 1):
        print(f"  {i}. {kb.get('title', '?')[:60]}")
        # 医生题显示 professional_content
        content = kb.get("professional_content") or kb.get("content", "")
        print(f"     " + content[:120].replace("\n", " ") + "...")


def demo_safety_gate():
    """演示 3：触发安全闸门（顺势疗法）"""
    print("\n" + "=" * 70)
    print("Demo 3：安全闸门触发（顺势疗法）")
    print("=" * 70)

    agent = ASAgent()
    out = agent.answer("顺势疗法能治好我的强直性脊柱炎吗？")

    print(f"\n[触发 {len(out['triggered_rules'])} 条质控规则]:")
    for r in out["triggered_rules"][:5]:
        typ = r.get("type", "?")
        if r.get("error"):  # medical_correction
            print(f"  · [{typ}] ❌ {r['error'][:60]}")
            print(f"           ✅ {r['correct'][:60]}")
        else:
            trig = r.get("rule") or r.get("trigger_condition") or "?"
            act = r.get("required_action") or r.get("action") or ""
            print(f"  · [{typ}] {trig[:70]}")
            if act:
                print(f"           → {act[:70]}")


def demo_save_prompt():
    """演示 4：把 system prompt 保存到文件，供外部 LLM 调用"""
    print("\n" + "=" * 70)
    print("Demo 4：保存 prompt 用于喂给底层 LLM")
    print("=" * 70)

    agent = ASAgent()
    out = agent.answer("AS 患者怀孕期间能用阿达木单抗吗？")

    output_file = Path(__file__).parent / "demo_prompt_output.txt"
    output_file.write_text(out["system_prompt"], encoding="utf-8")

    print(f"\n[已保存] {output_file}")
    print(f"  现在你可以把这个 prompt 喂给任何 LLM：")
    print(f"  $ openai api chat.completions.create \\")
    print(f"      -m gpt-4o-mini \\")
    print(f"      --system \"$(cat {output_file.name})\" \\")
    print(f"      --user \"AS 患者怀孕期间能用阿达木单抗吗？\"")


if __name__ == "__main__":
    print("AS Skill 快速上手示例")
    demo_patient_question()
    demo_physician_question()
    demo_safety_gate()
    demo_save_prompt()
    print("\n" + "=" * 70)
    print("All demos complete. 完整 API 见 scripts/answer.py")
    print("=" * 70)
