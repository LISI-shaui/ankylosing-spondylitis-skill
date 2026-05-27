#!/usr/bin/env python3
"""意图识别：A-J 模块 × a-d 维度 × patient/physician 受众
基于关键词词典 + 启发规则，无需 LLM 调用。
"""
import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# 模块关键词（A-J 10 个）
MODULE_KEYWORDS = {
    "A": ["疾病知识", "什么是", "病因", "发病", "流行病学", "HLA-B27",
          "遗传", "致病机制"],
    "B": ["症状", "诊断", "鉴别", "腰背痛", "晨僵", "炎性背痛", "影像",
          "MRI", "X 线", "纽约标准", "ASAS 分类"],
    "C": ["评估", "监测", "BASDAI", "ASDAS", "BASFI", "BASMI", "活动度",
          "炎症指标", "CRP", "ESR"],
    "D": ["治疗", "中医", "针灸", "顺势", "推拿", "理疗", "物理治疗",
          "替代医学", "中药"],
    "E": ["心理", "焦虑", "抑郁", "情绪", "PHQ-9", "GAD-7"],
    "F": ["循证", "PICO", "决策", "指南", "推荐"],
    "G": ["用药", "药物", "NSAIDs", "塞来昔布", "依托考昔", "TNF",
          "阿达木", "英夫利西", "IL-17", "司库奇尤", "JAK", "托法替布",
          "甲氨蝶呤", "柳氮磺吡啶", "生物制剂", "靶向药", "副作用",
          "禁忌", "停药", "调整"],
    "H": ["运动", "康复", "游泳", "瑜伽", "太极", "燕子飞", "锻炼",
          "拉伸", "扩胸"],
    "I": ["怀孕", "妊娠", "备孕", "哺乳", "儿童", "老年", "驾驶",
          "皮肤", "防晒", "饮食", "营养", "睡眠", "硬板床"],
    "J": ["教育", "科普", "建议", "生活方式", "戒烟", "病友"],
}

# 维度关键词
DIMENSION_KEYWORDS = {
    "a": ["病史", "采集", "问诊", "首发", "起病", "病程"],
    "b": ["家族", "遗传", "亲属", "父母", "兄弟"],
    "c": ["功能", "评估", "活动度", "BASFI", "BASMI", "走路", "弯腰"],
    "d": ["决策", "依据", "证据", "PICO", "对比", "推荐", "指南"],
}

# 患者特征词
PATIENT_HINTS = ["我", "我的", "我老", "怎么办", "怕", "担心", "害怕",
                 "请问", "能不能", "可以吗", "需要吗", "应该", "听说",
                 "网上", "我看到", "家里人"]

# 医生特征词（弱信号，需累加判断）
PHYSICIAN_HINTS = ["如何系统", "采集", "评估", "鉴别", "管理", "PICO",
                   "处方", "剂量", "禁忌", "首选", "次选", "策略",
                   "随访", "Schober", "Wexner", "DXA", "FRAX",
                   "ASDAS-CRP", "BASDAI", "BASFI", "BASMI", "MASES",
                   "对比", "推荐", "证据等级", "Cohort", "meta"]

# 医生特征词（强信号 — 出现 ≥1 个即判 physician）
PHYSICIAN_STRONG_TERMS = [
    "NSAIDs", "TNFi", "TNF-α", "TNF-a", "IL-17", "IL-17i", "JAK", "JAKi",
    "依那西普", "阿达木单抗", "英夫利西", "戈利木", "塞库奇尤", "依奇珠",
    "司库奇尤", "托法替布", "乌帕替尼", "巴瑞替尼",
    "甲氨蝶呤", "柳氮磺吡啶", "硫唑嘌呤",
    "影像学", "MRI 显示", "复发率", "OR=", "HR=", "RR=",
    "葡萄膜炎复发", "活动性骶髂关节炎", "X 线 ≥",
    "妊娠", "备孕期", "哺乳期", "产科联合", "黑框警告",
    "ESR", "CRP", "C反应蛋白", "血沉",
]


def _load_codebook():
    p = DATA_DIR / "intent_codebook.json"
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {}


def _score_module(text):
    scores = {}
    for code, kws in MODULE_KEYWORDS.items():
        s = sum(1 for kw in kws if kw in text)
        if s > 0:
            scores[code] = s
    return scores


def _score_dimension(text):
    scores = {}
    for code, kws in DIMENSION_KEYWORDS.items():
        s = sum(1 for kw in kws if kw in text)
        if s > 0:
            scores[code] = s
    return scores


def _detect_audience(text):
    patient = sum(1 for hint in PATIENT_HINTS if hint in text)
    physician_weak = sum(1 for hint in PHYSICIAN_HINTS if hint in text)
    # 强医生信号：只要出现 1 个专业药品/检验/影像术语 → physician
    physician_strong = sum(1 for kw in PHYSICIAN_STRONG_TERMS if kw in text)
    physician = physician_weak + physician_strong * 2  # 强信号 ×2 加权
    if physician_strong >= 1 and patient <= 1:
        return "physician", physician, patient
    if physician > patient:
        return "physician", physician, patient
    return "patient", patient, physician


def recognize_intent(question, codebook=None, audience_override=None):
    """识别意图。

    Args:
        question: 用户问题文本
        codebook: 可选，意图码表（默认从 data/intent_codebook.json 加载）
        audience_override: 'patient' / 'physician' / 'auto'（默认 auto）

    Returns:
        {
          "module": "G",
          "module_name": "用药管理",
          "dimension": "d",
          "dimension_name": "决策支持",
          "audience": "patient",
          "intent_code": "G-d-patient",
          "scores": {"module": {...}, "dimension": {...}},
        }
    """
    if codebook is None:
        codebook = _load_codebook()
    mods = codebook.get("modules", {})
    dims = codebook.get("dimensions", {})
    mod_desc = codebook.get("module_descriptions", {})
    dim_desc = codebook.get("dimension_descriptions", {})

    text = question.strip()
    module_scores = _score_module(text)
    dim_scores = _score_dimension(text)

    # 选 top module（无匹配则默认 A 疾病知识）
    if module_scores:
        module_code = max(module_scores, key=module_scores.get)
    else:
        module_code = "A"

    # 选 top dimension（无匹配则按模块默认 d 决策支持）
    if dim_scores:
        dim_code = max(dim_scores, key=dim_scores.get)
    else:
        dim_code = "d"

    # 受众
    if audience_override in ("patient", "physician"):
        audience = audience_override
        a_p, a_phy = 0, 0
    else:
        audience, a_p, a_phy = _detect_audience(text)

    return {
        "module": module_code,
        "module_name": mods.get(module_code, ""),
        "module_description": mod_desc.get(module_code, ""),
        "dimension": dim_code,
        "dimension_name": dims.get(dim_code, ""),
        "dimension_description": dim_desc.get(dim_code, ""),
        "audience": audience,
        "intent_code": f"{module_code}-{dim_code}-{audience}",
        "scores": {
            "module": module_scores,
            "dimension": dim_scores,
            "audience": {"patient_hints": a_p if audience == "patient" else a_phy,
                         "physician_hints": a_phy if audience == "patient" else a_p},
        },
    }


if __name__ == "__main__":
    import sys
    q = sys.argv[1] if len(sys.argv) > 1 else "我刚被诊断 AS，该了解什么？"
    res = recognize_intent(q)
    print(json.dumps(res, ensure_ascii=False, indent=2))
