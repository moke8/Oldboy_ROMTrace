# 翻译 Provider 拆分 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将翻译从数据源模块剥离，通过统一函数调度 Google 翻译和可配置的 OpenAI 兼容 AI 翻译。

**Architecture:** `translate_google.py` 与 `translate_deepseek.py` 分别封装具体请求，`translate_base.py` 根据 `translate_provider` 调度。UI 按 Provider 保存并回填 `translate_configs`，配置经平台层原样传入刮削流程。

**Tech Stack:** Python 3.8+、标准库 `urllib`、PySide6、`unittest`

## Global Constraints

- `translate_provider` 仅接受 `off`、`google`、`ai`。
- `translate_configs` 按 Provider 分组保存配置。
- 三个翻译模块均只使用函数，不引入类或全局客户端。
- 翻译失败返回原文且不中断刮削，不在日志中输出 Key。
- 不实现流式响应、重试、批量翻译、自定义提示词或额外 AI 参数。

---

### Task 1: 独立翻译模块与统一调度

**Files:**
- Create: `translate_google.py`
- Create: `translate_deepseek.py`
- Create: `translate_base.py`
- Modify: `datasource_base.py`
- Create: `tests/test_translate.py`
- Modify: `tests/test_datasource_base.py`

**Interfaces:**
- Produces: `translate_google.translate(text: str, target_lang: str) -> str`
- Produces: `translate_deepseek.translate(text: str, target_lang: str, config: dict) -> str`
- Produces: `translate_base.translate(text: str, target_lang: str, provider: str, configs: dict | None = None) -> str`

- [ ] **Step 1: 编写 Google、AI 和调度器失败测试**

在 `tests/test_translate.py` 覆盖 Google 自动源语言、AI URL 规范化、Bearer 请求头、请求体、响应提取、缺配置回退，以及 `off/google/ai/unknown` 分派；Mock `translate_google.urlopen`、`translate_deepseek.urlopen` 和两个实现函数。

- [ ] **Step 2: 运行测试确认失败**

Run: `.conda-env/bin/python -m unittest tests.test_translate -v`
Expected: FAIL，提示翻译模块不存在。

- [ ] **Step 3: 实现三个函数模块**

`translate_google.translate()` 迁移现有 Google 请求逻辑。`translate_deepseek.translate()` 将根地址规范化为 `/v1/chat/completions`，保留已有 `/v1`，完整端点不重复拼接；发送 `model` 与要求只返回译文的 `messages`。`translate_base.translate()` 对 `off` 返回原文，对 `google` 和 `ai` 调用对应函数，未知值回退原文。

- [ ] **Step 4: 删除数据源中的翻译职责并更新旧测试**

从 `datasource_base.py` 删除 `google_translate` 及不再需要的 `quote` 导入；将原 Google 测试移动到 `tests/test_translate.py`，保持数据源测试只验证数据源职责。

- [ ] **Step 5: 运行翻译测试**

Run: `.conda-env/bin/python -m unittest tests.test_translate tests.test_datasource_base -v`
Expected: PASS。

### Task 2: 设置界面与配置迁移

**Files:**
- Modify: `main.py`
- Modify: `tests/test_scrape_settings.py`

**Interfaces:**
- Produces: `ScrapeSettingsDialog.get_settings()` 返回 `translate_provider` 与完整 `translate_configs`
- Produces: `MainWindow.get_global_settings()` 转发上述两个字段

- [ ] **Step 1: 编写 Provider UI 失败测试**

在 `tests/test_scrape_settings.py` 验证默认 Provider 为 `google`；下拉框包含 `off/google/ai`；AI 被选中时三项输入可见；从 AI 切到 Google 再切回 AI 后，中转站、模型和 Key 均回填；`get_settings()` 保存完整分组配置；旧 `translate=False` 解析为 `off`。

- [ ] **Step 2: 运行 UI 测试确认失败**

Run: `QT_QPA_PLATFORM=off .conda-env/bin/python -m unittest tests.test_scrape_settings -v`
Expected: FAIL，提示 `translate_provider_combo` 不存在。

- [ ] **Step 3: 实现下拉框和按 Provider 回填**

用 `QComboBox` 替换 `translate_check`，数据值依次为 `off/google/ai`。新增 AI 中转站、模型、Key 输入框及容器；Provider 切换时先把控件值存入 `self._translate_configs[old_provider]`，再从新 Provider 配置回填，并只在 `ai` 时展示容器。

- [ ] **Step 4: 实现读取、保存和旧配置兼容**

初始化时深拷贝 `translate_configs`；新字段不存在时把旧 `translate` 布尔值映射到 `google/off`。更新默认设置、配置加载键、旧配置迁移键和全局设置返回值，不再生成新的 `translate` 字段。

- [ ] **Step 5: 运行 UI 测试**

Run: `QT_QPA_PLATFORM=off .conda-env/bin/python -m unittest tests.test_scrape_settings -v`
Expected: PASS。

### Task 3: 刮削流程接入统一调度器

**Files:**
- Modify: `scrape.py`
- Modify: `platform_base.py`
- Modify: `tests/test_scrape_logging.py`
- Modify: `tests/test_scrape_media.py`

**Interfaces:**
- Consumes: `translate_base.translate(text, target_lang, provider, configs)`
- Produces: `batch_scrape(..., translate_provider='google', translate_configs=None, ...)`

- [ ] **Step 1: 编写刮削调度失败测试**

更新测试参数为 `translate_provider='google'` 与 `translate_configs={'google': {}}`；Patch `scrape.translate_text`，验证描述、类型和标题翻译走统一入口，并验证 `off` 不调用翻译。配置日志断言 Provider 显示为“Google 翻译”“AI 翻译”或“关闭”，AI 日志只显示配置完整性。

- [ ] **Step 2: 运行刮削测试确认失败**

Run: `.conda-env/bin/python -m unittest tests.test_scrape_logging tests.test_scrape_media -v`
Expected: FAIL，提示新参数或 `translate_text` 不存在。

- [ ] **Step 3: 替换刮削参数和调用**

`scrape.py` 导入 `translate_base.translate as translate_text`；将布尔 `translate` 替换为 Provider 与配置。翻译启用条件改为 `translate_provider != 'off'`，两处翻译调用均传入目标语言、Provider 和完整配置。

- [ ] **Step 4: 更新平台参数传递与安全日志**

`platform_base.py` 的手动刷新和批量刮削都传递两个新字段。配置日志输出 Provider 名称、目标语言；AI 模式额外输出“配置完整/配置不完整”，不拼接配置原值。

- [ ] **Step 5: 运行刮削相关测试**

Run: `.conda-env/bin/python -m unittest tests.test_scrape_logging tests.test_scrape_media -v`
Expected: PASS。

### Task 4: 文档与完整验证

**Files:**
- Modify: `README.md`

**Interfaces:**
- Consumes: 已完成的 UI 配置和三个翻译函数模块
- Produces: 与实际项目结构、功能描述一致的用户文档

- [ ] **Step 1: 更新功能和项目结构文档**

将“支持 Google Translate 翻译”更新为“支持 Google 翻译和 OpenAI 兼容 AI 翻译”；在项目结构中列出 `translate_base.py`、`translate_google.py`、`translate_deepseek.py`，并从 `datasource_base.py` 描述中移除翻译。

- [ ] **Step 2: 运行全部测试**

Run: `QT_QPA_PLATFORM=off .conda-env/bin/python -m unittest discover -s tests -v`
Expected: PASS。

- [ ] **Step 3: 检查差异和敏感信息**

Run: `git diff --check && ! git diff | rg "Bearer [A-Za-z0-9]"`
Expected: 命令退出码为 0，且无空白错误或硬编码 Key。

- [ ] **Step 4: 提交实现**

Run: `git add translate_base.py translate_google.py translate_deepseek.py datasource_base.py main.py platform_base.py scrape.py README.md tests/test_translate.py tests/test_datasource_base.py tests/test_scrape_settings.py tests/test_scrape_logging.py tests/test_scrape_media.py && git commit -m "feat: 拆分可配置翻译 Provider"`
Expected: 仅提交上述翻译功能文件。

### Task 5: AI 翻译错误日志

**Files:**
- Modify: `translate_deepseek.py`
- Modify: `translate_google.py`
- Modify: `translate_base.py`
- Modify: `scrape.py`
- Modify: `tests/test_translate.py`
- Modify: `tests/test_scrape_logging.py`

**Interfaces:**
- Produces: 三个 `translate()` 函数接受可选 `log` 回调
- Produces: Provider 失败日志格式为 `[翻译] <模型或 Provider>: <中文原因>`

- [ ] **Step 1: 编写错误日志失败测试**

Mock AI 接口返回 `404 model_not_found`，断言日志为 `[翻译] MiniMax-M2.7: 该模型不存在，或当前 Key 无权访问。`；覆盖配置缺失、网络超时、无效响应和调度器日志传递，并断言日志不包含 Key。

- [ ] **Step 2: 运行测试确认失败**

Run: `.conda-env/bin/python -m unittest tests.test_translate -v`
Expected: FAIL，提示 `translate()` 不接受 `log` 或未生成错误日志。

- [ ] **Step 3: 实现脱敏中文错误日志**

Provider 函数增加 `log=None`，用内部函数输出 `[翻译]` 日志。AI 捕获 `HTTPError` 并解析响应中的 `error.code` 与 `error.message`；`model_not_found` 映射为固定中文原因，其他错误使用脱敏后的服务端消息。配置、网络、超时和解析错误分别输出明确中文原因。

- [ ] **Step 4: 贯通调度器和刮削日志**

`translate_base.translate()` 将 `log` 传给具体 Provider，`scrape.py` 两处调用传入当前 `log`；未变化结果记录“未生成新译文”，避免再次笼统描述失败。

- [ ] **Step 5: 运行针对性和完整测试**

Run: `.conda-env/bin/python -m unittest tests.test_translate tests.test_scrape_logging -v`
Expected: PASS。

Run: `QT_QPA_PLATFORM=offscreen .conda-env/bin/python -m unittest discover -s tests -v`
Expected: PASS。
