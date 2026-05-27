# Contributing to AS Skill

欢迎贡献！本项目接受三类贡献，按门槛从低到高：

| 类型 | 你需要的技能 | 实例 |
|------|------------|------|
| 🐛 **A. 报 bug / 数据修正** | 任何人都能做 | KB 里某条文献过期了；意图识别误判 |
| 📚 **B. 扩展 AS 知识库** | 临床医生 / 风湿免疫研究者 | 加入新的临床指南、补充罕见亚型 |
| 🧬 **C. 把方法学平移到其他专科** | 数据科学家 + 专科医生协作 | 做"RA Skill"、"银屑病关节炎 Skill"等 |

---

## A. 报 bug 或建议数据修正（最容易）

### 提 Issue 的最低要求

打开 [GitHub Issue](../../issues/new)，标题模板：

- `[bug] xxx`：代码运行异常
- `[data] xxx`：知识库内容有错或过期
- `[doc] xxx`：文档有误
- `[feat] xxx`：功能建议

正文请包含：
1. **复现步骤**（哪条命令、哪段代码触发的）
2. **期望行为**（你认为应该输出什么）
3. **实际行为**（实际输出了什么 + 完整报错堆栈）
4. **环境**：Python 版本 + OS + jieba 版本

### 数据修正 PR 模板

```bash
# 1. fork 后克隆
git checkout -b fix/kb-DX_001-update-asas-2024

# 2. 改 data/clinical_kb.json，注意：
#    - 不能编造文献（必须给 PMID / DOI / 真实期刊）
#    - id / module 字段不变
#    - 同时改 patient_content + professional_content + search_text

# 3. 跑测试
python tests/test_basic.py
# 必须 15/15 通过

# 4. 提交
git commit -m "data: update DX_001 ASAS criteria to 2024 revision"
git push -u origin fix/kb-DX_001-update-asas-2024
# 然后在 GitHub 上发起 PR
```

---

## B. 扩展 AS 知识库（中等门槛）

### 适合谁

- 临床医生（风湿免疫科 / 全科）
- 医学生 / 规培医师
- 健康教育工作者

### 步骤

#### 1. 决定加什么

打开 `data/clinical_kb.json` 看现有 67 条覆盖了哪些。下面是欢迎补充的方向：

- **罕见亚型**：青少年型 SpA、外周型 SpA、IBD 相关脊柱关节炎
- **新指南**：ASAS-EULAR 后续修订、各国本土指南
- **共病场景**：AS + 糖尿病 / AS + 心血管病 / AS + 老年综合评估
- **生物制剂新药**：新上市的 IL-17i / JAKi / 双靶点
- **特殊人群**：妊娠/哺乳/老年/儿科/亚临床期

#### 2. 写一条 KB 条目（模板）

```json
{
  "id": "DX_068",
  "title": "ASAS 中轴 SpA 分类标准 2024 修订",
  "module": "B",
  "module_name": "症状诊断",
  "year": "2024",
  "evidence_level": "分类标准",
  "source": "Author X et al., Ann Rheum Dis 2024;XX:XXX-XXX (真实 PMID/DOI)",
  "professional_content": "（200-400 字 · 给医生看的循证内容，含分类标准临床细则、敏感性/特异性、与原版差异等）",
  "patient_content": "（80-150 字 · 给患者看的大白话翻译，含 1 个比喻 + 1-2 个具体行动）",
  "search_text": "（≤ 600 字 · 给 TF-IDF 检索用，可包含 title + professional_content 的精炼版）",
  "key_points": ["要点 1", "要点 2", "要点 3"]
}
```

#### 3. 验证

```bash
# 跑 schema 校验
python -c "
import json
e = json.load(open('data/clinical_kb.json'))
new_entries = [x for x in e['entries'] if x['id'].startswith('DX_068')]
assert new_entries, '新条目未找到'
for x in new_entries:
    for k in ['id', 'title', 'module', 'source', 'professional_content', 'patient_content']:
        assert k in x and x[k], f'{x[\"id\"]} 缺字段 {k}'
print('Schema OK')
"

# 跑回归测试
python tests/test_basic.py
```

#### 4. 同步更新质控规则（可选）

如果你的新 KB 引入了新的禁忌、安全红线、常见误区，请同步加到 `data/quality_rules.json`：

```json
{
  "type": "safety_rule",     // medical_correction / safety_rule / common_mistake / quality_template
  "severity": "critical",     // critical / high / medium / low
  "rule": "（触发条件，比如：当问题涉及 JAKi 时）",
  "required_action": "（必须的动作，比如：附 FDA 黑框警告）",
  "source_question": "M0XX",
  "reference": "FDA Safety Communication 2024-XX"
}
```

#### 5. PR

```bash
git checkout -b kb/add-asas-2024-criteria
git add data/clinical_kb.json data/quality_rules.json
git commit -m "kb: add 5 entries for ASAS 2024 axSpA criteria revision"
git push -u origin kb/add-asas-2024-criteria
```

PR 描述请包含：
- 加了哪些条目（id 列表）
- 主要参考文献
- 是否影响 quality_rules（是 → 列出新增规则 id）

PR 会在 GitHub Actions CI 自动跑测试，需全部绿勾。

---

## C. 把方法学平移到其他专科（高门槛 · 强烈欢迎）

### 你将贡献一个独立的 `xx-skill/` 仓库或本仓库的子目录

不是给本仓库加 KB，而是**复刻整套方法学**到你关心的疾病（如 RA / Lupus / Gout / Crohn）。

### 协作建议

我们建议**数据科学家 + 专科医生 2 人组**：
- **专科医生**：负责知识库内容、质控规则、专家洞察
- **数据科学家**：负责 SHAP/LIME/SPA 归因脚本、检索器

### 平移路线图（约 4-8 周）

| 阶段 | 工作 | 产出 |
|------|------|------|
| Week 1-2 | 收集 40-60 道目标疾病典型问题，3-5 个 LLM 各答一遍 | raw_responses.json |
| Week 2-3 | 临床医生盲评（3 人独立打分 D1-D6 + 选最优） | reviewer_evaluations.json |
| Week 3-4 | 跑 SHAP / LIME / SPA 三层归因 | shap.json / lime.json / spa.json |
| Week 4-5 | 整理 30-80 条临床循证 KB（带真实文献） | clinical_kb.json |
| Week 5-6 | 写 30-50 条质控规则 | quality_rules.json |
| Week 6-7 | 复刻 scripts/ 各文件（基本只需改关键词词典） | scripts/ |
| Week 7-8 | 测试 + 文档 + 提 PR | 完整 xx-skill/ |

### 引用本工作

如果你平移成功并发表论文 / 参赛，**请引用**：

```bibtex
@misc{as_skill_2026,
  title  = {AS Skill: A Three-Layer Attribution-Based Trustworthy Medical
            Dialogue Framework for Ankylosing Spondylitis},
  year   = {2026},
  url    = {https://github.com/LISI-shaui/ankylosing-spondylitis-skill}
}
```

---

## 通用准则

### ✅ 永远做

- 真实文献（PMID / DOI / 期刊年份），**绝不编造**
- 同步改 patient_content + professional_content + search_text
- 提 PR 前跑 `python tests/test_basic.py`，必须 15/15
- 用清晰的 commit 信息（`kb:` / `fix:` / `doc:` / `feat:` 前缀）

### ❌ 绝不做

- 把患者个人信息（姓名/病历号/联系方式）写进 KB
- 在 KB 里给具体患者诊断建议（KB 是科普/参考，不是诊断书）
- 提交未经验证的"偏方/秘方"
- 在引用文献处填占位符（如 "TBD" / "待补充"）

### 关于医学免责

本项目是**医学教育与研究工具**，不是医疗器械软件。任何贡献都默认你同意：
- 你贡献的内容会落入 MIT 协议
- 你不会基于本 Skill 给具体患者做诊断建议
- 你会在使用时附医学免责声明

---

## 行为准则

请遵守 [Contributor Covenant](https://www.contributor-covenant.org/version/2/1/code_of_conduct/)。简单说：**互相尊重 + 对事不对人 + 学术诚信**。

---

## 联系方式

- 一般问题：GitHub Issue
- 学术合作 / 跨专科平移协作：在 Issue 里 @ 维护者，留下你的研究方向

**感谢你愿意贡献。让医学知识更平权，需要更多人参与。** 🙏
