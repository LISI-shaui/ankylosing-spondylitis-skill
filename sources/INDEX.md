# Sources Index

> 本目录归档 AS Skill 知识库引用的**原始源文档**。每加一份源就在这里登记一行，并把对应的处理后 entry 用 `source.doc_id` 字段反向链接回来。
>
> **规则**：
> - 源文档 ID 命名：`src-{system}-{NNN}`（`system` = `western` / `tcm` / `integrated`）
> - 文件名格式：`{年份}-{简称}-{出处}.md`
> - 原始 PDF/docx 不提交（见 `sources/_raw/.gitignore`），只提交抽取后的 markdown
> - 每加一份源**必须**填齐：标题、作者、出处、年份、抽取日期、对应 KB entry 数

---

## Western medicine (现有 67 条 entry 的源)

| Doc ID | 标题 | 作者 | 出处 | 年份 | 抽取日期 | KB entries |
|---|---|---|---|---|---|---|
| src-western-001 | ASAS-EULAR Management Recommendations | van der Heijde D, et al. | Ann Rheum Dis | 2017/2022 update | (历史导入) | 多条 `DX_*`/`TX_*` |
| src-western-002 | ACR/SPARTAN/SAA 2019 Update | Ward MM, et al. | Arthritis Rheumatol 71(10):1599-1613 | 2019 | (历史导入) | 多条 |
| src-western-003 | ASAS axSpA Classification Criteria | Rudwaleit M, et al. | Ann Rheum Dis 68:777-783 | 2009 | (历史导入) | `DX_001` |
| src-western-004 | Modified New York Criteria | van der Linden S, et al. | Arthritis Rheum 27:361-368 | 1984 | (历史导入) | `DX_002` |

> 注：v1.0.0 的 67 条西医 entry 是从多份指南/共识汇总而来，未逐条登记。下次维护时再补 doc_id 反向映射。

---

## TCM / Integrated Chinese & Western medicine

| Doc ID | 标题 | 作者 / 颁布机构 | 出处 | 年份 | 抽取日期 | KB entries |
|---|---|---|---|---|---|---|
| src-tcm-001 | 强直性脊柱炎中西医结合医疗质量控制指标专家共识（2021版） | 陶庆文, 鄢泽然, 孔维萍, 徐愿, 张楠（中日友好医院中医风湿病科）；北京中西医结合学会风湿病专业委员会备案号 2021Z031A2 | 中日友好医院学报 35(2) | 2021 | 2026-05-28 | `int-001`, `int-002`, `tcm-003`, `tcm-008` |
| src-tcm-002 | 强直性脊柱炎中西医结合诊疗指南 | 何东仪, 程鹏, 汪荣盛, 范鋆钰（上海光华中西医结合医院关节内科）；中国中西医结合学会标准化技术委员会颁布 | 上海医药 44(13) | 2023 | 2026-05-28 | `tcm-001` 至 `tcm-013`（除 003/008） |

---

## How to register a new source

```bash
# 1. 把原始文件丢进 sources/_raw/（不会被 commit）
cp ~/Downloads/some-guideline.pdf sources/_raw/

# 2. 抽取成 markdown（手工或用 pandoc / python-docx）
#    保存到 sources/{western|tcm|integrated}/{年份}-{简称}-{出处}.md

# 3. 在本表里加一行，分配下一个 src-{system}-{NNN} ID

# 4. 在写 KB entry 时，source.doc_id 字段填上面分配的 ID
```

每份源都应该是**可独立追溯**的：拿着 INDEX.md 里登记的标题 + 出处，应该能在 PubMed / 万方 / CNKI 上把原文找回来。
