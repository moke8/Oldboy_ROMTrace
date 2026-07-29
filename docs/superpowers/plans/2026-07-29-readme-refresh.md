# README 内容更新 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 更新 README，使翻译错误日志、AI 翻译配置和 PS1 字典支持与当前代码一致。

**Architecture:** 保持 README 现有章节结构，只扩充功能列表、平台表格、使用说明和项目结构。内容以已提交翻译功能和当前已实现 PS1 字典代码为依据。

**Tech Stack:** Markdown、Git

## Global Constraints

- 不记录真实中转站、模型或 Key。
- 不添加逐提交更新日志。
- 不修改安装、构建、License 或作者信息。

---

### Task 1: 更新 README 功能说明

**Files:**
- Modify: `README.md`

**Interfaces:**
- Consumes: `translate_base.py`、`translate_deepseek.py`、`translate_google.py`、`platform_ps1.py`、`ps1_game_db.py`
- Produces: 与当前功能一致的用户说明和项目结构索引

- [ ] **Step 1: 更新平台与功能描述**

将 PS1 解析方式写为“`SYSTEM.CNF` 序列号 → 内置字典标准英文名”；扩充翻译和日志功能项，说明 Provider 选择、AI 配置、失败回退和脱敏中文错误。

- [ ] **Step 2: 新增翻译配置小节**

在使用方法中说明“关闭 / Google 翻译 / AI 翻译”三种选项；AI 需要中转站、模型、Key，中转站兼容根地址、`/v1` 和完整 `/chat/completions`。

- [ ] **Step 3: 更新项目结构**

补充 `ps1_game_db.py` 和 `build_ps1_db.py`，分别描述 PS1 序列号映射和字典生成脚本。

- [ ] **Step 4: 验证文档**

Run: `git diff --check -- README.md`
Expected: 无输出，退出码为 0。

Run: `grep -n "AI 翻译\|PS1_GAME_DB\|翻译失败" README.md`
Expected: 三类说明均有匹配，且 README 不包含真实 Key。
