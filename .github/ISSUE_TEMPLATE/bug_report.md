---
name: 🐛 Bug 报告
about: 代码运行异常 / 输出与预期不符
title: '[bug] '
labels: bug
assignees: ''
---

## 复现步骤
```bash
# 你跑的具体命令
python scripts/answer.py "..."
```

## 期望行为
说明你认为应该输出什么。

## 实际行为
```
（贴完整输出 + 完整报错堆栈）
```

## 环境信息
- OS: <!-- Windows 11 / macOS 14 / Ubuntu 22.04 -->
- Python: <!-- 3.x.x -->
- jieba: <!-- pip show jieba | grep Version -->
- 你 fork 的 commit: <!-- git rev-parse HEAD -->

## 测试是否通过？
```bash
python tests/test_basic.py
# 贴最后几行输出
```

## 其他线索
<!-- 例如：仅在特定 KB 条目上触发 / 仅在 patient 受众触发 / 跟其他 Skill 同时挂载触发 -->
