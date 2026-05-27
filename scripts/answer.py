#!/usr/bin/env python3
"""AS Skill 主入口 — 输入用户问题，输出增强后的 system prompt + 检索证据。

CLI 用法：
    python scripts/answer.py "AS 患者吃布洛芬有用吗？" --audience patient
    python scripts/answer.py --interactive

Python 库用法：
    from scripts.answer import ASAgent
    agent = ASAgent()
    out = agent.answer("我刚被诊断 AS")
"""
import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from retrieval import TfIdfIndex
from intent_recognition import recognize_intent
from prompt_builder import build_system_prompt

ROOT = SCRIPT_DIR.parent
DATA = ROOT / "data"


class ASAgent:
    """AS 专科问诊智能体（Skill 化版本）。"""

    def __init__(self, top_k_kb=5, top_k_insights=3, audience="auto"):
        self.top_k_kb = top_k_kb
        self.top_k_insights = top_k_insights
        self.default_audience = audience

        # 加载所有数据
        self.codebook = self._load("intent_codebook.json")
        self.kb = self._load("clinical_kb.json").get("entries", [])
        self.rules = self._load("quality_rules.json").get("entries", [])
        self.insights = self._load("reviewer_insights.json").get("entries", [])
        self.qa_templates = self._load("qa_templates.json").get("entries", [])
        self.attribution = self._load("attribution_evidence.json")

        # 建索引
        self.kb_index = TfIdfIndex([self._extract_text(e) for e in self.kb])
        self.insight_index = TfIdfIndex(
            [self._extract_text(e) for e in self.insights])

    @staticmethod
    def _load(filename):
        p = DATA / filename
        if not p.exists():
            return {}
        return json.loads(p.read_text(encoding="utf-8"))

    @staticmethod
    def _extract_text(entry):
        """从条目中提取可检索文本（兼容多种 schema）。"""
        parts = []
        for k in ("search_text", "title", "content",
                  "professional_content", "patient_content",
                  "pattern", "improvement", "question", "template",
                  "trigger_condition", "required_action", "rule", "action",
                  "source"):
            v = entry.get(k)
            if v and isinstance(v, str):
                parts.append(v)
        kp = entry.get("key_points", [])
        if isinstance(kp, list):
            parts.extend(str(p) for p in kp)
        return " ".join(parts)

    def _filter_by_intent(self, entries, intent):
        """按意图软过滤：同模块的优先匹配，其他保留参与排序。
        全 True 表示不过滤；通过 boost 实现"优先同模块"由 TF-IDF 排序保证。
        """
        mod = intent["module"]
        mask = []
        for e in entries:
            m = e.get("module") or e.get("module_code") or ""
            module_ok = (m == mod) or (str(m).startswith(mod)) or (not m)
            mask.append(bool(module_ok))
        # 若全 False（一个匹配模块都没有），退回全 True
        if not any(mask):
            mask = [True] * len(entries)
        return mask

    def _trigger_rules(self, question, intent):
        """检查哪些质控规则被问题触发（支持 medical_correction / safety_rule /
        common_mistake / quality_template 四种类型）。"""
        triggered = []
        text = (question + " " + intent.get("module_name", "") +
                " " + intent.get("dimension_name", ""))
        # 关键词触发器（出现在问题里就触发任何含此关键词的规则）
        HOT_KEYWORDS = [
            "顺势", "替代医学", "中药", "针灸", "推拿", "草药", "民间",
            "停药", "怀孕", "妊娠", "备孕", "哺乳", "母乳",
            "JAK", "黑框", "禁忌", "心衰", "感染", "活疫苗", "结核",
            "葡萄膜炎", "TNFi", "IL-17", "MASES", "BASDAI", "BASFI",
            "骨质疏松", "DXA", "FRAX", "激素", "糖皮质激素",
        ]
        hot_hits = [kw for kw in HOT_KEYWORDS if kw in text]
        for rule in self.rules:
            rule_text = (
                (rule.get("error", "") or "") + " " +
                (rule.get("correct", "") or "") + " " +
                (rule.get("trigger_condition", "") or "") + " " +
                (rule.get("rule", "") or "") + " " +
                (rule.get("required_action", "") or "")
            )
            # ① 任一 hot kw 同时出现在问题与规则文本
            if any(kw in rule_text for kw in hot_hits):
                triggered.append(rule)
                continue
            # ② 模块/source_question 匹配
            if rule.get("module") == intent["module"]:
                triggered.append(rule)
                continue
            # ③ 全局 safety_rule 一律保留（高优先级）
            if rule.get("type") == "safety_rule" and rule.get("severity") == "critical":
                # 但避免太多——只保留前 3 条临界 safety
                if sum(1 for r in triggered
                       if r.get("type") == "safety_rule") < 3:
                    triggered.append(rule)
        return triggered[:6]

    def answer(self, question, audience=None):
        """主接口。

        Args:
            question: 用户问题
            audience: 'patient' / 'physician' / None（自动识别）

        Returns:
            dict 含 system_prompt / intent / retrieved / triggered_rules /
            insights / attribution
        """
        aud_override = audience if audience in ("patient", "physician") else None
        if self.default_audience in ("patient", "physician"):
            aud_override = aud_override or self.default_audience

        intent = recognize_intent(question, self.codebook, aud_override)

        # 检索 KB
        kb_mask = self._filter_by_intent(self.kb, intent)
        kb_hits = self.kb_index.query(question, top_k=self.top_k_kb,
                                      mask=kb_mask)
        retrieved_kb = [self.kb[idx] for idx, _ in kb_hits]

        # 检索 insights
        ins_mask = self._filter_by_intent(self.insights, intent)
        ins_hits = self.insight_index.query(question,
                                            top_k=self.top_k_insights,
                                            mask=ins_mask)
        retrieved_insights = [self.insights[idx] for idx, _ in ins_hits]

        # 触发规则
        triggered_rules = self._trigger_rules(question, intent)

        # 组装 system prompt
        system_prompt = build_system_prompt(
            question, intent, retrieved_kb, triggered_rules,
            retrieved_insights, self.attribution
        )

        return {
            "intent": intent,
            "retrieved_kb": retrieved_kb,
            "triggered_rules": triggered_rules,
            "retrieved_insights": retrieved_insights,
            "attribution_summary": {
                "shap_top": self.attribution.get("shap", {}).get(
                    f"{intent['audience']}_top_contributor", {}),
                "lime_top_phrases": dict(
                    list(self.attribution.get("lime", {}).get(
                        "top_phrases", {}).items())[:5]),
                "spa_top_terms": dict(
                    list(self.attribution.get("spa", {}).get(
                        "top_terms", {}).items())[:5]),
            },
            "system_prompt": system_prompt,
        }


def main():
    parser = argparse.ArgumentParser(
        description="AS Skill — 强直性脊柱炎专科问诊智能体")
    parser.add_argument("question", nargs="?",
                        help="用户问题。不提供则进入交互模式。")
    parser.add_argument("--audience", choices=["patient", "physician", "auto"],
                        default="auto", help="目标受众（默认自动识别）")
    parser.add_argument("--top-k-kb", type=int, default=5)
    parser.add_argument("--top-k-insights", type=int, default=3)
    parser.add_argument("--format", choices=["json", "prompt"], default="json",
                        help="输出格式：json (完整) / prompt (仅 system prompt)")
    parser.add_argument("--interactive", action="store_true",
                        help="交互式模式")
    args = parser.parse_args()

    agent = ASAgent(top_k_kb=args.top_k_kb,
                    top_k_insights=args.top_k_insights,
                    audience=args.audience)

    if args.interactive:
        print("=" * 60)
        print("AS Skill 交互式 (输入 quit 退出)")
        print("=" * 60)
        while True:
            q = input("\n问：").strip()
            if q.lower() in ("quit", "exit", "q"):
                break
            if not q:
                continue
            out = agent.answer(q)
            if args.format == "prompt":
                print(out["system_prompt"])
            else:
                print(json.dumps({
                    "intent": out["intent"],
                    "retrieved_kb_count": len(out["retrieved_kb"]),
                    "triggered_rules_count": len(out["triggered_rules"]),
                    "first_kb": out["retrieved_kb"][:1],
                    "system_prompt_preview": out["system_prompt"][:600] + "...",
                }, ensure_ascii=False, indent=2))
    else:
        if not args.question:
            parser.error("需要提供 question 参数，或使用 --interactive")
        out = agent.answer(args.question)
        if args.format == "prompt":
            print(out["system_prompt"])
        else:
            print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
