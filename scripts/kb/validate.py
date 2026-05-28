#!/usr/bin/env python3
"""KB validator (zero-dependency, two-tier).

校验策略：
- **Strict tier**（含 `system` 字段的新条目，v1.1+）：
    * id 必须匹配 `^(tcm|int|west)-\\d{3}$`
    * module ∈ A-J
    * system ∈ {western, tcm, integrated}
    * evidence_grade 必须合法
    * source.doc_id 必须在 sources/INDEX.md 注册
    * professional_content / patient_content / search_text 非空
    * cross_refs 指向已存在的 entry id
- **Lenient tier**（无 `system` 字段的历史条目，v1.0）：
    * 仅要求 id 存在且唯一；其他问题计入"历史债"统计但不阻塞
    * 用 `--strict-legacy` 把历史条目也跑严格校验

跑法：
    python scripts/kb/validate.py                 # 默认（新条目严格，历史宽松）
    python scripts/kb/validate.py --strict-legacy # 全部严格
    python scripts/kb/validate.py data/tcm_kb.json
"""
import json
import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parent.parent.parent
DATA = ROOT / "data"
SOURCES_INDEX = ROOT / "sources" / "INDEX.md"

KB_FILES = ["clinical_kb.json", "tcm_kb.json"]

ALLOWED_MODULES = set("ABCDEFGHIJ")
ALLOWED_DIMENSIONS = set("abcd")
ALLOWED_SYSTEMS = {"western", "tcm", "integrated"}
ALLOWED_AUDIENCES = {"patient", "physician", "both"}

NEW_ID_PATTERN = re.compile(r"^(tcm|int|west)-\d{3}$")
LEGACY_ID_PATTERN = re.compile(r"^[A-Za-z]+[-_][A-Za-z0-9]+$")
EVIDENCE_GRADE_PATTERN = re.compile(
    r"^(Oxford-(1|2)[A-D]|consensus-[A-C]|expert-opinion|systematic-review|RCT|meta-analysis|none)$"
)
DOC_ID_PATTERN = re.compile(r"^src-(western|tcm|integrated)-\d{3}$")

STRICT_REQUIRED = [
    "id", "title", "module", "module_name", "system",
    "professional_content", "patient_content", "search_text",
]
LENIENT_REQUIRED = ["id", "title"]


def load_registered_doc_ids():
    if not SOURCES_INDEX.exists():
        return set()
    text = SOURCES_INDEX.read_text(encoding="utf-8")
    return set(re.findall(r"src-(?:western|tcm|integrated)-\d{3}", text))


def is_strict_entry(entry):
    return "system" in entry


def validate_strict(entry, label, idx, all_ids, registered_doc_ids):
    errs = []
    eid = entry.get("id", f"<no-id at index {idx}>")
    prefix = f"[{label} #{idx} {eid}] (strict)"

    for field in STRICT_REQUIRED:
        if field not in entry:
            errs.append(f"{prefix} missing field: {field}")
        elif not entry[field] or (isinstance(entry[field], str) and not entry[field].strip()):
            errs.append(f"{prefix} field '{field}' empty")

    if "id" in entry:
        if not NEW_ID_PATTERN.match(entry["id"]):
            errs.append(f"{prefix} id '{entry['id']}' does not match new pattern {NEW_ID_PATTERN.pattern}")
        if entry["id"] in all_ids:
            errs.append(f"{prefix} duplicate id")
        else:
            all_ids.add(entry["id"])

    if entry.get("module") not in ALLOWED_MODULES:
        errs.append(f"{prefix} module '{entry.get('module')}' not in A-J")

    if "dimension" in entry and entry["dimension"] not in ALLOWED_DIMENSIONS:
        errs.append(f"{prefix} dimension '{entry['dimension']}' not in a-d")

    if entry.get("system") not in ALLOWED_SYSTEMS:
        errs.append(f"{prefix} system '{entry.get('system')}' not in {ALLOWED_SYSTEMS}")

    if "audience" in entry and entry["audience"] not in ALLOWED_AUDIENCES:
        errs.append(f"{prefix} audience '{entry['audience']}' not in {ALLOWED_AUDIENCES}")

    if "evidence_grade" in entry:
        if not EVIDENCE_GRADE_PATTERN.match(entry["evidence_grade"]):
            errs.append(f"{prefix} evidence_grade '{entry['evidence_grade']}' invalid")

    src = entry.get("source")
    if isinstance(src, dict):
        doc_id = src.get("doc_id")
        if not doc_id:
            errs.append(f"{prefix} source missing doc_id")
        elif not DOC_ID_PATTERN.match(doc_id):
            errs.append(f"{prefix} source.doc_id '{doc_id}' bad format")
        elif registered_doc_ids and doc_id not in registered_doc_ids:
            errs.append(f"{prefix} source.doc_id '{doc_id}' not registered in sources/INDEX.md")
    elif not src:
        errs.append(f"{prefix} missing source")

    if "search_text" in entry and isinstance(entry["search_text"], str):
        if len(entry["search_text"].strip()) < 20:
            errs.append(f"{prefix} search_text too short")

    return errs


def validate_lenient(entry, label, idx, all_ids):
    """Lenient checks — only catches truly broken legacy entries; counts other issues for stats."""
    errs = []
    warnings = []
    eid = entry.get("id", f"<no-id at index {idx}>")
    prefix = f"[{label} #{idx} {eid}] (legacy)"

    for field in LENIENT_REQUIRED:
        if field not in entry or not entry[field]:
            errs.append(f"{prefix} missing required field: {field}")

    if "id" in entry:
        if not LEGACY_ID_PATTERN.match(entry["id"]):
            errs.append(f"{prefix} id '{entry['id']}' malformed")
        if entry["id"] in all_ids:
            errs.append(f"{prefix} duplicate id")
        else:
            all_ids.add(entry["id"])

    if entry.get("module") not in ALLOWED_MODULES:
        warnings.append(f"{prefix} module '{entry.get('module')}' not in A-J (legacy)")

    for field in ("professional_content", "patient_content"):
        v = entry.get(field, "")
        if not v or not v.strip():
            warnings.append(f"{prefix} field '{field}' empty (legacy data debt)")

    if "search_text" in entry and isinstance(entry["search_text"], str):
        if len(entry["search_text"].strip()) < 20:
            warnings.append(f"{prefix} search_text short (legacy)")

    return errs, warnings


def validate_file(path, registered, all_ids, strict_legacy):
    label = path.name
    if not path.exists():
        return [f"[{label}] file not found"], [], 0, 0

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return [f"[{label}] JSON decode error: {e}"], [], 0, 0

    entries = data.get("entries", [])
    if not isinstance(entries, list):
        return [f"[{label}] 'entries' not a list"], [], 0, 0

    errs, warnings = [], []
    n_strict = n_legacy = 0
    for idx, entry in enumerate(entries):
        if not isinstance(entry, dict):
            errs.append(f"[{label} #{idx}] entry not a dict")
            continue
        if is_strict_entry(entry):
            n_strict += 1
            errs.extend(validate_strict(entry, label, idx, all_ids, registered))
        else:
            n_legacy += 1
            if strict_legacy:
                errs.extend(validate_strict(entry, label, idx, all_ids, registered))
            else:
                le, lw = validate_lenient(entry, label, idx, all_ids)
                errs.extend(le)
                warnings.extend(lw)
    return errs, warnings, n_strict, n_legacy


def validate_cross_refs(kb_files_data, all_ids):
    errs = []
    for label, data in kb_files_data.items():
        for idx, entry in enumerate(data.get("entries", [])):
            if not isinstance(entry, dict):
                continue
            for ref in entry.get("cross_refs", []) or []:
                if ref not in all_ids:
                    errs.append(
                        f"[{label} #{idx} {entry.get('id', '?')}] cross_ref '{ref}' missing"
                    )
    return errs


def main():
    args = sys.argv[1:]
    strict_legacy = "--strict-legacy" in args
    targets = [a for a in args if not a.startswith("--")]
    if not targets:
        targets = [str(DATA / f) for f in KB_FILES]

    registered = load_registered_doc_ids()
    print(f"Registered doc_ids in sources/INDEX.md: {len(registered)}")
    print(f"Mode: {'STRICT for all entries' if strict_legacy else 'STRICT for new (with system field), LENIENT for legacy'}")

    all_ids = set()
    kb_files_data = {}
    all_errs, all_warnings = [], []
    total_strict = total_legacy = 0

    for t in targets:
        path = Path(t)
        errs, warns, n_strict, n_legacy = validate_file(path, registered, all_ids, strict_legacy)
        all_errs.extend(errs)
        all_warnings.extend(warns)
        total_strict += n_strict
        total_legacy += n_legacy
        if path.exists():
            try:
                kb_files_data[path.name] = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                pass
        n_entries = len(kb_files_data.get(path.name, {}).get("entries", []))
        print(f"  {path.name}: {n_entries} entries (strict: {n_strict}, legacy: {n_legacy})")

    all_errs.extend(validate_cross_refs(kb_files_data, all_ids))

    print(f"\nTotal entries: {len(all_ids)}  (strict-mode: {total_strict}, legacy-mode: {total_legacy})")

    if all_warnings:
        print(f"\n[WARN] {len(all_warnings)} legacy data debt issues (run with --strict-legacy to enforce):")
        max_shown = 5
        for w in all_warnings[:max_shown]:
            print(f"  {w}")
        if len(all_warnings) > max_shown:
            print(f"  ... ({len(all_warnings) - max_shown} more)")

    if all_errs:
        print(f"\n[FAIL] {len(all_errs)} blocking errors:\n")
        for e in all_errs:
            print(f"  {e}")
        sys.exit(1)
    else:
        print("\n[OK] All KB files pass validation.")
        sys.exit(0)


if __name__ == "__main__":
    main()
