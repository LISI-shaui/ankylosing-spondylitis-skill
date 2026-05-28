# KB Contributing Guide

> 这份文档说明**怎么往 AS Skill 知识库（KB）加新内容**。给项目维护者用，也给未来的社区贡献者用。

---

## 核心原则

1. **每条 entry 必须有出处** —— `source` 字段必须是结构化对象（含 `doc_id`），指向 `sources/INDEX.md` 里登记的源文档。没出处的内容不进 KB。
2. **每条新 entry 必须带 `system` 字段** —— `western` / `tcm` / `integrated` 三选一。新内容默认走 strict 校验。
3. **schema 是契约** —— 见 [`schemas/kb_entry.schema.json`](../schemas/kb_entry.schema.json)。所有 entry 必须能通过 `scripts/kb/validate.py`。
4. **commit 前跑校验 + 测试** —— `python scripts/kb/validate.py && python tests/test_basic.py`，红了不准 push。
5. **改动 KB 内容必须升版本号** —— `data/tcm_kb.json` 顶部的 `_kb_version` 字段按 [SemVer](https://semver.org/) 规则升：
   - 加新 entry → minor +1（如 1.1.0 → 1.2.0）
   - 改已有 entry 的内容 → patch +1（如 1.1.0 → 1.1.1）
   - 改 schema → major +1

---

## 加新内容的完整流程

### 步骤 1：把源文档归档到 `sources/`

```bash
# 1.1 把原始 PDF / docx 放进 sources/_raw/（不会被 commit，已在 .gitignore）
cp ~/Downloads/某指南.pdf sources/_raw/

# 1.2 抽取成 markdown（推荐用 pandoc，如果是 docx 也可以用 python-docx）
pandoc sources/_raw/某指南.pdf -o sources/{western|tcm|integrated}/{年份}-{简称}-{出处}.md

# 1.3 用现有源 markdown 作为模板（sources/tcm/2023-诊疗指南-上海医药.md），
#     在新文件顶部补齐元数据：Doc ID、抽取日期、标题、作者、出处等
```

### 步骤 2：在 `sources/INDEX.md` 登记新源

在对应表格里加一行：

```markdown
| src-{system}-{下一个序号:03d} | 标题 | 作者 / 颁布机构 | 期刊 卷(期) | 年 | 抽取日期 | 待填 |
```

> Doc ID 命名规则：`src-{system}-{NNN}`，例如 `src-tcm-003`。`{system}` 必须是 `western` / `tcm` / `integrated`。

### 步骤 3：写 KB entries 到 `data/{xx_kb}.json`

每条 entry 必须包含的字段（参考 [`data/tcm_kb.json`](../data/tcm_kb.json) 任意一条作为模板）：

```json
{
  "id": "tcm-018",
  "title": "条目简短标题",
  "module": "D",
  "module_name": "治疗方法",
  "dimension": "d",
  "system": "tcm",
  "year": "2024",
  "evidence_level": "系统评价",
  "evidence_grade": "Oxford-2C",
  "source": {
    "doc_id": "src-tcm-003",
    "title": "原文标题",
    "authors": ["作者1", "作者2"],
    "journal": "期刊名",
    "year": 2024,
    "section": "原文章节号 + 章节标题"
  },
  "professional_content": "面向医生的专业表述...",
  "patient_content": "面向患者的通俗表述...",
  "search_text": "用于 TF-IDF 检索的长文本，建议合并 title + professional_content + patient_content 的关键词",
  "key_points": ["要点1", "要点2", "..."],
  "tags": ["主题词1", "主题词2"],
  "cross_refs": ["tcm-002"],
  "added_date": "2026-05-28",
  "reviewed_by": "你的 GitHub username"
}
```

### 步骤 4：升 KB 版本号

```bash
# 改 data/{xx_kb}.json 顶部的 _kb_version 字段
# 加 N 条新 entry → minor +1
# 改 entry 内容 → patch +1
```

### 步骤 5：跑校验 + 测试

```bash
python scripts/kb/validate.py        # 必须全过（new 严格 + legacy 宽松）
python tests/test_basic.py           # 15 项回归测试必须全过
```

如果你加的内容影响了某个题目的检索结果（比如挤掉了老 entry 的 top-3），`test_basic.py` 可能会失败 —— 这是好事，说明回归测试在工作。判断：

- 失败的题目**新答案更好** → 更新 `test_basic.py` 里的期望值，同时在 commit message 里说明
- 失败的题目**新答案更差** → 调整新 entry 的 search_text 关键词、或重新评估它是否该进 KB

### 步骤 6：commit + push

```bash
git add sources/ data/ schemas/
git commit -m "feat(kb): import {源简称} ({N} new {system} entries)"
git push
```

commit message 用 [Conventional Commits](https://www.conventionalcommits.org/)：
- 加新 entry：`feat(kb): ...`
- 修 entry 内容：`fix(kb): ...`
- 改 schema：`refactor(kb): ...` 或 `feat(kb)!: ...`（! 表示 breaking）

---

## 字段填写规范

### `id`

- 格式：`{system}-{NNN}`，三位数字
- `system` ∈ `tcm` / `int` / `west`（注意：`west-` 是给将来新增的西医条目用，不是给历史条目改的）
- 序号在该 system 内全局唯一，不允许复用已删除的号
- 历史条目（v1.0 的 67 条）保留原始 ID 格式（如 `DX_001`, `FAQ_002`），不强制改名

### `module` / `dimension`

- `module` ∈ A-J，对应 [`data/intent_codebook.json`](../data/intent_codebook.json)
- `dimension` ∈ a-d；不确定就填 `d`（决策支持）
- `module_name` 必须与 `module` 对应，不能错配

### `system`

- `western`：纯西医内容（ASAS / ACR / EULAR 等指南、西药、影像学等）
- `tcm`：纯中医内容（中医病名、辨证分型、方剂、针灸、外治法等）
- `integrated`：跨中西医（合并症的中西医结合治疗、质控指标、中医结合西医分期等）

### `evidence_grade`

结构化证据等级，必须匹配下列正则之一：

| 模式 | 含义 | 例 |
|---|---|---|
| `Oxford-{1\|2}{A\|B\|C\|D}` | Oxford 证据分级 | `Oxford-1B`, `Oxford-2C` |
| `consensus-{A\|B\|C}` | 专家共识等级 | `consensus-A`（A 级推荐 ≥85% 一致率） |
| `expert-opinion` | 专家意见（无更高证据） | — |
| `systematic-review` | 系统综述 | — |
| `RCT` | 单个 RCT | — |
| `meta-analysis` | meta 分析 | — |
| `none` | 暂无明确证据 | — |

### `source`

**新条目必须用结构化对象**，必含 `doc_id`：

```json
"source": {
  "doc_id": "src-tcm-002",
  "title": "原文完整标题",
  "authors": ["第一作者", "通讯作者"],
  "journal": "期刊",
  "year": 2023,
  "volume": "44(13)",
  "section": "12.3 针灸疗法",
  "pmid": null,
  "doi": null
}
```

`doc_id` 必须在 `sources/INDEX.md` 里注册过；否则校验器会报错。

### `professional_content` / `patient_content`

- **必须两个都写**（不是写一个就行）
- `professional_content`：面向医生，循证为主，**带证据等级和具体数值**
- `patient_content`：面向患者，通俗语言，**带具体行动建议**（不只是讲道理）
- 长度建议：每个 100-300 字。太短显得草率，太长污染 prompt 体积

### `search_text`

- TF-IDF 检索用的关键词长文本
- 建议把 `title` + `professional_content` + `patient_content` 的关键词都 dump 进去（重复 OK）
- 主要医学术语用中文 + 英文都列一遍（如 "ASDAS AS 疾病活动评分"）
- 长度 ≥ 20 字符（校验器最低要求）

### `key_points`

5-7 条要点，**每条不超过 30 字**。这些会显示在 prompt 的"关键要点"区，应该精炼且互不重复。

### `tags`

自由词；用于将来按主题筛选 / 统计。建议复用已有 tag（看现有 entry）。

### `cross_refs`

指向其他 entry 的 ID 列表。校验器会检查每个引用是否真存在。

---

## 校验器输出含义

```bash
$ python scripts/kb/validate.py

Registered doc_ids in sources/INDEX.md: 6
Mode: STRICT for new (with system field), LENIENT for legacy
  clinical_kb.json: 67 entries (strict: 0, legacy: 67)
  tcm_kb.json: 17 entries (strict: 17, legacy: 0)

Total entries: 84  (strict-mode: 17, legacy-mode: 67)

[WARN] 69 legacy data debt issues (run with --strict-legacy to enforce):
  ...
[OK] All KB files pass validation.
```

- **strict 模式**：新条目（含 `system` 字段）走严格检查
- **legacy 模式**：v1.0 历史条目走宽松检查
- **[WARN]**：历史数据债（67 条 v1.0 entry 里有 17 条内容为空、若干条 module 不在 A-J）—— 不阻塞，但应在 v1.2 或 v2.0 里清理
- **[FAIL]**：阻塞错误，必须修复才能继续
- **[OK]**：通过

跑 `--strict-legacy` 可以把历史条目也按新标准检查（用于清理历史债）：

```bash
python scripts/kb/validate.py --strict-legacy
```

---

## 常见加内容场景

### 场景 1：加一份新的指南/共识

走完整的"步骤 1-6"。预计耗时 30-60 分钟（其中 50% 是把指南章节拆成 KB entry 并辨证、定证据等级）。

### 场景 2：单独加一条 entry（无新源）

如果对应的源已经在 `sources/INDEX.md` 里登记过，跳过步骤 1-2，直接：

1. 编辑对应 `data/{xx_kb}.json`
2. 复用现有 `doc_id`，填新的 entry
3. 升 patch 版本号
4. 跑校验 + 测试 → commit

### 场景 3：修改一条已有 entry

1. 改 entry 内容
2. 更新该 entry 的 `last_review_date`
3. 升 patch 版本号
4. 跑校验 + 测试 → commit

### 场景 4：删除一条 entry

1. 移除 entry
2. **检查 `cross_refs`**：如果其他 entry 引用了它，要一并清理引用
3. 升 patch 版本号
4. 跑校验（会检查 cross_refs 完整性）→ commit

### 场景 5：清理 v1.0 历史数据债

不是一次性任务。建议每次维护时顺手清理 5-10 条：把空内容补上、把 `FAQ_*` 这类不规范的 module 改成 A-J 中合适的、补齐 `system`/`evidence_grade`/`source.doc_id` 字段。清理完一批就升 minor。

---

## FAQ

**Q：能不能不写 `patient_content`？我加的是纯医生用的指南。**
A：必须写。`ASAgent(audience="auto")` 默认会自动识别受众，没有 `patient_content` 会导致患者题被错误地用专业表述回答。最差也写一句"建议在风湿科医师指导下评估和治疗"。

**Q：我手上的源是非中文/非英文（比如日文 / 德文指南），怎么办？**
A：先翻译成中文（保留原文标题作为 `source.title`），抽取后的 markdown 用中文写。`search_text` 同时放中英文关键词。

**Q：source 是中文期刊但没有 PMID/DOI，怎么填？**
A：`pmid` / `doi` 字段设为 `null`，把卷号期号填到 `volume`。校验器只检查 `doc_id` 必须注册。

**Q：怎么判断我加的内容算 `tcm` 还是 `integrated`？**
A：纯中医（病名、证型、方剂）→ `tcm`；西医诊断框架下的中西医协同（合并症、质控、跨体系评估）→ `integrated`；纯西医 → `western`。如果一条 entry 同时讲西医和中医治疗，按"主体内容"归类。

**Q：能不能直接让 LLM 帮我把 PDF 拆成 entry？**
A：可以，但 **必须人工逐条审核**，特别是：(1) 证据等级标对（原文是 1B 还是 2C，不能蒙）；(2) 安全警示不遗漏（雷公藤生殖毒性、IL-17 抑制剂禁用 IBD 等）；(3) `professional_content` 引用的数值要回查原文。LLM 抽出来的草稿当起点，不当成品。

---

## 升 Lite → Pro 的信号

当出现下列任意一个，就该把 KB 工具链从 Lite 升到 Pro（加 `extract_source.py` / `add_entry.py` / `stats.py` / `diff.py`）：

- [ ] KB 总条数超过 200
- [ ] 有 ≥3 个外部贡献者提 PR 加 KB
- [ ] 一次加新源耗时超过 1 小时
- [ ] 你想把 KB 渲染成可搜索的文档站（mkdocs）
- [ ] 项目扩展到第 2 个专科（RA / 痛风等）

到时候参考根目录 README 第 192 行的扩展方案，或重新读 [`docs/KB-ARCHITECTURE.md`](KB-ARCHITECTURE.md)（Pro 档位会创建这个文件）。
