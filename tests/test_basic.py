#!/usr/bin/env python3
"""AS Skill 基本回归测试。
跑法：cd ankylosing-spondylitis-skill && python tests/test_basic.py
"""
import sys
import json
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from answer import ASAgent
from intent_recognition import recognize_intent


PASS = "\033[32m✓\033[0m"
FAIL = "\033[31m✗\033[0m"


def assert_true(cond, msg):
    if cond:
        print(f"  {PASS} {msg}")
        return True
    else:
        print(f"  {FAIL} {msg}")
        return False


def test_intent_recognition():
    print("\n[Test 1] 意图识别")
    cases = [
        ("我刚被诊断为强直性脊柱炎", "patient", "B"),
        ("AS 患者吃布洛芬 NSAIDs 一线选择是什么", "physician", "G"),
        ("怀孕期间还能继续打阿达木单抗吗", "physician", "G"),
        ("游泳和燕子飞哪个更适合 AS", "patient", "H"),
    ]
    passed = 0
    for q, expected_aud, expected_mod in cases:
        res = recognize_intent(q)
        ok = res["audience"] == expected_aud and res["module"] == expected_mod
        if assert_true(ok, f'"{q[:30]}..." → {res["module"]}-{res["audience"]} (期望 {expected_mod}-{expected_aud})'):
            passed += 1
    return passed, len(cases)


def test_kb_retrieval():
    print("\n[Test 2] KB 检索")
    agent = ASAgent()
    out = agent.answer("ASAS 中轴型脊柱关节炎分类标准是什么")
    passed = 0
    n = 4
    passed += assert_true(len(out["retrieved_kb"]) > 0, f"检索到至少 1 条 KB（实际 {len(out['retrieved_kb'])}）")
    passed += assert_true(
        any("ASAS" in (kb.get("title", "") or "") for kb in out["retrieved_kb"]),
        "Top KB 含 ASAS 关键词")
    passed += assert_true(len(out["system_prompt"]) > 500,
                          f"system prompt 至少 500 字（实际 {len(out['system_prompt'])}）")
    passed += assert_true(
        "ASAS-EULAR" in out["system_prompt"] or "ACR" in out["system_prompt"]
        or "Rudwaleit" in out["system_prompt"],
        "system prompt 含真实文献来源")
    return passed, n


def test_safety_gate():
    print("\n[Test 3] 安全闸门触发")
    agent = ASAgent()
    out = agent.answer("顺势疗法能治好我的强直性脊柱炎吗")
    passed = 0; n = 2
    passed += assert_true(len(out["triggered_rules"]) > 0,
                          f"顺势疗法问题触发 ≥1 条规则（实际 {len(out['triggered_rules'])}）")
    rule_texts = " ".join(json.dumps(r, ensure_ascii=False)
                          for r in out["triggered_rules"])
    passed += assert_true("顺势" in rule_texts or "停药" in rule_texts
                          or "偏方" in rule_texts,
                          "触发的规则含'顺势/停药/偏方'相关内容")
    return passed, n


def test_audience_adaptation():
    print("\n[Test 4] 受众自动适配")
    agent = ASAgent()
    # 患者用语
    out_p = agent.answer("我刚被诊断 AS，特别害怕")
    # 医生用语
    out_d = agent.answer("AS 患者使用 TNFi 后葡萄膜炎复发率与 IL-17i 对比")
    passed = 0; n = 2
    passed += assert_true(out_p["intent"]["audience"] == "patient",
                          f"患者用语 → audience=patient（实际 {out_p['intent']['audience']}）")
    passed += assert_true(out_d["intent"]["audience"] == "physician",
                          f"医生用语 → audience=physician（实际 {out_d['intent']['audience']}）")
    return passed, n


def test_attribution_injection():
    print("\n[Test 5] 三层归因证据注入")
    agent = ASAgent()
    out = agent.answer("AS 患者的核心治疗目标是什么")
    passed = 0; n = 3
    passed += assert_true("SHAP" in out["system_prompt"], "SHAP 证据已注入")
    passed += assert_true("LIME" in out["system_prompt"], "LIME 证据已注入")
    passed += assert_true("SPA" in out["system_prompt"], "SPA 证据已注入")
    return passed, n


def main():
    print("=" * 60)
    print("AS Skill 回归测试")
    print("=" * 60)
    total_passed = total = 0
    for fn in [test_intent_recognition, test_kb_retrieval,
               test_safety_gate, test_audience_adaptation,
               test_attribution_injection]:
        p, n = fn()
        total_passed += p
        total += n
    print("\n" + "=" * 60)
    print(f"结果：{total_passed} / {total} 通过 "
          f"({total_passed/total*100:.0f}%)")
    print("=" * 60)
    return 0 if total_passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
