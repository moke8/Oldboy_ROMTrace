# NDS DAT 英文标题映射设计

## 背景

部分日版 Nintendo DS ROM 会把相同的日文标题写入横幅的日语、英语、法语、德语、意大利语和西班牙语槽位。现有解析器将英语槽直接作为 `title_en`，因此会出现 `title` 与 `title_en` 都是日文的情况。例如，游戏代码 `AYDJ` 的《伊苏 DS》六个西文/日文槽位均为 `イースDS`。

项目已取得 No-Intro 完整数据库 `Nintendo - Nintendo DS (Decrypted) (20260724-122857).dat`。该数据库包含 `AYDJ → Ys DS (Japan)` 等游戏代码与规范名称的对应关系。

## 目标

- 保留 ROM 横幅标题作为本地化显示标题 `title`。
- 优先通过 NDS Game Code 查表得到规范英文搜索标题 `title_en`。
- 不在运行时解析约 3 MB 的 DAT 文件。
- 保持未知 Game Code 的现有回退行为。
- 实现方式与项目现有 GBA Game Code 数据库保持一致。

## 非目标

- 不通过 CRC、MD5、SHA1 或 SHA256 精确识别 ROM 修订版本。
- 不在运行时联网补充 Game Code 映射。
- 不改变 NDS 图标、发行商及多语言横幅解析逻辑。
- 不修改其他游戏平台的标题规则。

## 数据生成

新增 `build_nds_db.py`，使用 Python 标准库 `xml.etree.ElementTree` 解析 No-Intro DAT：

1. 遍历 `<game>` 元素并读取其 `name` 属性。
2. 遍历游戏下的 `<rom>` 元素并读取 `serial` 属性。
3. 只接受长度为 4 且由字母或数字组成的序列号。
4. 同一序列号对应多个 DAT 条目时，保留 DAT 中首次出现的名称，以匹配 GBA 生成器的简单、确定性策略。
5. 按序列号排序后生成 `nds_game_db.py`，其中只包含静态 `NDS_GAME_DB` 字典和来源、条目数说明。

生成器的默认输入文件名与当前下载的 DAT 文件一致。生成结果纳入项目，应用运行时不依赖原始 DAT。

## 运行时标题选择

`platform_nds.extract_nds_info()` 读取 Game Code 后执行以下规则：

1. `title` 继续使用 `parse_nds_titles()` 按界面语言选出的横幅标题；没有横幅标题时沿用 ROM Header 标题和文件名回退。
2. 用 Game Code 查询 `NDS_GAME_DB`。
3. 查表命中时，移除 No-Intro 名称中的括号后缀，将结果作为 `title_en`。例如 `Ys DS (Japan)` 清理为 `Ys DS`。
4. 查表未命中时，`title_en` 沿用当前规则：英语横幅槽位优先，否则回退到 `title`。

因此 `AYDJ` 的解析结果为：

```text
title: イースDS
title_en: Ys DS
game_code: AYDJ
```

## 异常与兼容性

- 数据库缺少代码不会导致解析失败，只会进入原有回退路径。
- 汉化 ROM 通常仍保留原始 Game Code，因此可以得到原版规范英文标题。
- Game Code 并非版本级唯一标识；同一代码的修订版或特殊转储可能共用一个简化标题。这符合本次轻量查表目标。
- 生成器遇到格式不合法的 XML 时直接报错，避免静默生成不完整数据库。

## 测试

采用测试驱动方式增加 NDS 平台测试：

- 已知代码 `AYDJ`：横幅英语槽与日语槽相同时，`title` 保持日文且 `title_en` 为 `Ys DS`。
- 未知代码：`title_en` 继续使用英语横幅槽或 `title` 回退。
- No-Intro 名称清理：只移除括号区域/语言后缀，不破坏标题主体。
- 生成器：从最小 DAT 夹具提取有效四位序列号、忽略无效序列号，并对重复序列号保留首个名称。

完成后运行新增测试及现有完整测试集，确认没有回归。
