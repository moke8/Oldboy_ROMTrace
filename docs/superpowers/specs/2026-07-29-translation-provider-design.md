# 翻译 Provider 拆分设计

## 目标

将翻译实现从数据源和刮削主流程中剥离。用户可在“关闭”“Google 翻译”“AI 翻译”之间选择，AI 翻译兼容 OpenAI `chat/completions` 接口，并允许配置中转站、模型和 Key。

## 配置

全局配置使用以下结构：

```json
{
  "translate_provider": "off",
  "translate_configs": {
    "google": {},
    "ai": {
      "base_url": "",
      "model": "",
      "api_key": ""
    }
  }
}
```

`translate_provider` 仅接受 `off`、`google`、`ai`。`translate_configs` 按 Provider 分组保存配置，便于后续新增翻译服务且不会覆盖其他 Provider 的已有设置。

旧配置中的 `translate: true` 迁移为 `translate_provider: google`，`translate: false` 迁移为 `translate_provider: off`。迁移只在新字段不存在时生效。

## 设置界面

原“翻译”复选框替换为下拉框，选项依次为“关闭”“Google 翻译”“AI 翻译”。

选择 AI 翻译时显示中转站、模型和 Key 输入框；选择其他项时隐藏。切换选项前先将当前 Provider 的输入值写入内存中的 `translate_configs`，切换后从目标 Provider 的配置中回填控件，因此反复切换不会丢失已输入内容。保存设置时再次收集当前 Provider 配置并持久化完整的 `translate_configs`。

## 模块边界

- `translate_google.py` 提供 Google 翻译函数，只负责构造请求、解析响应和失败回退。
- `translate_deepseek.py` 提供 AI 翻译函数，接收中转站、模型和 Key，调用 OpenAI 兼容的 `chat/completions` 接口。
- `translate_base.py` 提供统一调度函数，根据 Provider 选择具体实现；调用方不直接导入具体 Provider。
- `scrape.py` 只调用 `translate_base` 的统一入口，不再依赖 `datasource_base.google_translate`。
- `datasource_base.py` 删除 Google 翻译实现，仅保留数据源注册表和共享网络工具。

三个翻译模块均使用函数实现，不引入类或全局客户端状态。

## 调用流程

刮削配置将 `translate_provider` 和 `translate_configs` 从主界面传递到平台调度，再传入 `batch_scrape()`。当 Provider 不为 `off` 且目标语言存在时，`scrape.py` 调用统一翻译函数处理描述、类型和符合现有条件的标题。

统一入口接收原文、目标语言、Provider 和 Provider 配置。Google Provider 使用现有公共接口；AI Provider 从 `translate_configs.ai` 读取配置。AI 请求提示要求只返回译文，不添加解释或 Markdown。

AI 中转站地址兼容三种填写方式：站点根地址、以 `/v1` 结尾的地址、完整的 `/chat/completions` 地址。调度前规范化为最终请求地址，避免重复拼接路径。

## 失败与安全

空文本和无需翻译的英文目标保持原文。缺少 AI 中转站、模型或 Key、网络异常、非成功 HTTP 状态、JSON 格式错误或响应缺少译文时均返回原文，不中断批量刮削。

翻译日志保留开始、完成和失败状态。配置日志可显示 Provider，以及 AI 配置是否完整，但不得输出 API Key。

## 测试

- Google 翻译请求、响应解析与异常回退。
- AI 请求地址规范化、请求头和请求体。
- AI 响应解析、缺少配置和异常回退。
- 统一调度对 `off`、`google`、`ai` 和未知 Provider 的处理。
- 设置界面切换 Provider 时保存并回填已有配置。
- 旧 `translate` 布尔配置向新字段的兼容迁移。
- 刮削流程通过统一调度器翻译元数据和标题。

## 范围限制

本次不实现流式响应、重试、批量合并翻译、可编辑提示词或额外 AI 参数，也不改变现有标题翻译条件和目标语言列表。
