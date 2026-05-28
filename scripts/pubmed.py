#!/usr/bin/env python3
"""PubMed 实时检索 — 零依赖（urllib + xml.etree）。

用 NCBI E-utilities 在 PubMed 上检索 AS 相关的最新文献，
配合 ASAgent 输出的 system prompt 一起喂给 LLM。

接口：
    search_pubmed(query, max_results=3, recent_years=3) -> list[dict]
    extract_pubmed_query(question, intent) -> str

PubMed E-utilities 文档：
    https://www.ncbi.nlm.nih.gov/books/NBK25497/
速率限制：
    无 key   ≤ 3 req/sec  （demo 单访客足够）
    有 key   ≤ 10 req/sec （设置 NCBI_API_KEY 环境变量启用）
"""
import os
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from threading import Lock

EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
TIMEOUT = 10  # 秒
USER_AGENT = "as-skill-demo/1.1 (https://github.com/LISI-shaui/ankylosing-spondylitis-skill)"
NCBI_KEY = os.environ.get("NCBI_API_KEY", "").strip()

# ─────────── 缓存 ───────────
_CACHE = {}  # query → (timestamp, results)
_CACHE_TTL = 3600  # 1h
_CACHE_LOCK = Lock()
_MAX_CACHE = 100


def _cached(query):
    with _CACHE_LOCK:
        item = _CACHE.get(query)
        if item and time.time() - item[0] < _CACHE_TTL:
            return item[1]
    return None


def _put_cache(query, results):
    with _CACHE_LOCK:
        if len(_CACHE) >= _MAX_CACHE:
            _CACHE.pop(next(iter(_CACHE)))
        _CACHE[query] = (time.time(), results)


# ─────────── 中英术语映射（AS 高频词）───────────
CN2EN = {
    # 疾病名
    "强直性脊柱炎": "ankylosing spondylitis",
    "axSpA": "axial spondyloarthritis",
    "中轴型脊柱关节炎": "axial spondyloarthritis",
    "脊柱关节炎": "spondyloarthritis",
    "骶髂关节炎": "sacroiliitis",
    "葡萄膜炎": "uveitis",
    "炎症性肠病": "inflammatory bowel disease",
    "克罗恩病": "Crohn disease",
    "溃疡性结肠炎": "ulcerative colitis",
    "骨质疏松": "osteoporosis",
    "抑郁": "depression",
    "焦虑": "anxiety",
    # 药物（西医）
    "阿达木单抗": "adalimumab",
    "英夫利西单抗": "infliximab",
    "依那西普": "etanercept",
    "戈利木单抗": "golimumab",
    "司库奇尤单抗": "secukinumab",
    "依奇珠单抗": "ixekizumab",
    "托法替尼": "tofacitinib",
    "非戈替尼": "filgotinib",
    "乌帕替尼": "upadacitinib",
    "柳氮磺吡啶": "sulfasalazine",
    "甲氨蝶呤": "methotrexate",
    "沙利度胺": "thalidomide",
    "布洛芬": "ibuprofen",
    "塞来昔布": "celecoxib",
    "双氯芬酸": "diclofenac",
    "萘普生": "naproxen",
    # 药物类（中医/中药提取物）
    "雷公藤": "Tripterygium wilfordii",
    "雷公藤多苷": "Tripterygium glycosides",
    "白芍总苷": "total glucosides of paeony",
    "青藤碱": "sinomenine",
    "正清风痛宁": "sinomenine",
    # 类别
    "TNFi": "TNF inhibitors",
    "TNF 抑制剂": "TNF inhibitors",
    "肿瘤坏死因子抑制剂": "TNF inhibitors",
    "IL-17": "IL-17",
    "IL-17 抑制剂": "IL-17 inhibitors",
    "JAKi": "JAK inhibitors",
    "JAK 抑制剂": "JAK inhibitors",
    "白介素-17 抑制剂": "IL-17 inhibitors",
    "生物制剂": "biologics",
    "NSAIDs": "NSAIDs",
    "非甾体抗炎药": "NSAIDs",
    "csDMARDs": "conventional DMARDs",
    "bDMARDs": "biological DMARDs",
    # 评估
    "ASDAS": "ASDAS",
    "BASDAI": "BASDAI",
    "BASFI": "BASFI",
    "ASQoL": "ASQoL",
    # 状态
    "孕期": "pregnancy",
    "怀孕": "pregnancy",
    "妊娠": "pregnancy",
    "哺乳": "breastfeeding",
    "母乳": "breastfeeding",
    "备孕": "preconception",
    # 中医
    "督灸": "Du-moxibustion",
    "温针灸": "warm needling moxibustion",
    "针灸": "acupuncture",
    "中医": "traditional Chinese medicine",
    "中药": "Chinese herbal medicine",
}


def extract_pubmed_query(question: str, intent: dict = None) -> str:
    """从中文问题里抽出 PubMed 检索词。
    始终把 "ankylosing spondylitis" 作为锚定主词；附加 question 中出现的 CN→EN 术语。
    """
    if not question:
        return "ankylosing spondylitis"

    terms = ["ankylosing spondylitis"]
    seen = set(terms)

    # 命中术语
    for cn, en in CN2EN.items():
        if cn in question and en not in seen:
            terms.append(en)
            seen.add(en)

    # 主题词限定最近 3 个搜索词，避免 PubMed 召回过少
    main_terms = terms[:4]
    if len(main_terms) == 1:
        # 只有锚定词，加点动态线索：附着点炎、孕期、合并症等通用关键词
        return main_terms[0]
    return " AND ".join(f'"{t}"' if " " in t else t for t in main_terms)


# ─────────── HTTP ───────────
def _http_get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return resp.read()


def _build_url(endpoint: str, **params) -> str:
    if NCBI_KEY:
        params["api_key"] = NCBI_KEY
    qs = urllib.parse.urlencode(params)
    return f"{EUTILS}/{endpoint}?{qs}"


# ─────────── 主接口 ───────────
def search_pubmed(query: str, max_results: int = 3, recent_years: int = 3) -> list[dict]:
    """返回 list of dict: {pmid, title, authors, journal, year, abstract, url}
    失败时返回空列表，不抛异常 — demo 必须降级运行。
    """
    if not query.strip():
        return []
    cache_key = f"{query}|{max_results}|{recent_years}"
    cached = _cached(cache_key)
    if cached is not None:
        return cached

    try:
        # ESearch — 查 PMID
        esearch_url = _build_url(
            "esearch.fcgi",
            db="pubmed",
            term=f"({query}) AND (\"last {recent_years} years\"[PDat])",
            retmax=max_results,
            sort="date",
            retmode="xml",
        )
        esearch_xml = _http_get(esearch_url)
        root = ET.fromstring(esearch_xml)
        pmids = [el.text for el in root.findall(".//IdList/Id") if el.text]

        if not pmids:
            _put_cache(cache_key, [])
            return []

        # EFetch — 抓 abstract
        efetch_url = _build_url(
            "efetch.fcgi",
            db="pubmed",
            id=",".join(pmids),
            rettype="abstract",
            retmode="xml",
        )
        efetch_xml = _http_get(efetch_url)
        results = _parse_efetch(efetch_xml)
        _put_cache(cache_key, results)
        return results
    except Exception as e:
        print(f"[pubmed] search failed: {type(e).__name__}: {e}")
        _put_cache(cache_key, [])  # 缓存失败结果，1h 内不重试
        return []


def _parse_efetch(xml_bytes: bytes) -> list[dict]:
    """从 efetch XML 抽 PubMed 文章字段。"""
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        return []

    out = []
    for article in root.findall(".//PubmedArticle"):
        try:
            pmid_el = article.find(".//PMID")
            pmid = pmid_el.text if pmid_el is not None else ""

            title_el = article.find(".//ArticleTitle")
            title = _text(title_el)

            journal_el = article.find(".//Journal/Title")
            journal = _text(journal_el)

            year_el = article.find(".//Journal/JournalIssue/PubDate/Year")
            year = _text(year_el)
            if not year:
                medline_date_el = article.find(".//Journal/JournalIssue/PubDate/MedlineDate")
                year = (medline_date_el.text or "")[:4] if medline_date_el is not None else ""

            authors = []
            for auth_el in article.findall(".//AuthorList/Author")[:3]:
                ln = auth_el.find("LastName")
                init = auth_el.find("Initials")
                if ln is not None and ln.text:
                    a = ln.text
                    if init is not None and init.text:
                        a += f" {init.text}"
                    authors.append(a)

            abs_texts = []
            for abs_el in article.findall(".//Abstract/AbstractText"):
                t = _text(abs_el)
                if t:
                    label = abs_el.attrib.get("Label", "")
                    abs_texts.append(f"**{label}**: {t}" if label else t)
            abstract = " ".join(abs_texts)[:1200]  # 截断防过长

            out.append({
                "pmid": pmid,
                "title": title,
                "authors": authors,
                "journal": journal,
                "year": year,
                "abstract": abstract,
                "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else "",
            })
        except Exception:
            continue
    return out


def _text(el) -> str:
    """处理可能含 sub/sup/i 子标签的 XML 文本。"""
    if el is None:
        return ""
    return "".join(el.itertext()).strip()


def format_for_prompt(results: list[dict]) -> str:
    """把 PubMed 结果格式化进 system prompt 的一段。"""
    if not results:
        return ""
    lines = [
        "",
        "## 📡 PubMed 实时检索（最近 3 年）— 把这些最新证据纳入回答",
        "",
    ]
    for i, r in enumerate(results, 1):
        authors_str = ", ".join(r["authors"][:2]) + (" et al." if len(r["authors"]) > 2 else "")
        lines.append(
            f"**[{i}] PMID {r['pmid']} ({r['year']})** — *{r['journal']}*  \n"
            f"{r['title']}  \n"
            f"作者：{authors_str}  \n"
            f"摘要：{r['abstract'][:600]}{'...' if len(r['abstract']) > 600 else ''}  \n"
        )
    lines.append("")
    lines.append(
        "⚠️ 回答时若引用上述文献，**务必标注 PMID**；若结论与本地 KB 冲突，"
        "以最新文献为准并说明依据。"
    )
    return "\n".join(lines)


def format_for_ui(results: list[dict]) -> str:
    """把 PubMed 结果格式化成 UI 显示用的 Markdown。"""
    if not results:
        return "_(PubMed 实时检索：无结果或暂不可用)_"
    parts = [f"**共检索到 {len(results)} 篇最近 3 年文献**\n"]
    for i, r in enumerate(results, 1):
        authors_str = ", ".join(r["authors"][:2]) + (" et al." if len(r["authors"]) > 2 else "")
        url = r["url"] or "#"
        parts.append(
            f"### [{i}] [{r['title']}]({url})\n"
            f"- **PMID**：`{r['pmid']}` · {r['year']} · *{r['journal']}*\n"
            f"- **作者**：{authors_str}\n"
            f"- **摘要**：{r['abstract'][:500]}{'...' if len(r['abstract']) > 500 else ''}\n"
        )
    return "\n".join(parts)


# ─────────── CLI 自测 ───────────
if __name__ == "__main__":
    import json
    import sys

    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    q = sys.argv[1] if len(sys.argv) > 1 else "AS 患者怀孕了能继续用阿达木单抗吗"
    pq = extract_pubmed_query(q)
    print(f"Question: {q}")
    print(f"PubMed query: {pq}")
    print("Searching ...")
    rs = search_pubmed(pq, max_results=3)
    print(f"Got {len(rs)} results.\n")
    for r in rs:
        print(json.dumps({k: v for k, v in r.items() if k != "abstract"}, ensure_ascii=False, indent=2))
        print()
