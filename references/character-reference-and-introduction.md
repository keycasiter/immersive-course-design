# 人物参考与首次出场契约

本文件拥有视频人物研究、身份连续性与首次出场介绍。新视频计划采用 `schema_version=1.1`；1.0 可读取，但没有校验此契约，报告须明确提示。旧课只在授权的视频改稿范围迁移。

## 先研究，再定义形象

在编写人物形象或生成提示词前，对每个有身份或教学作用的人物查找原始材料、可靠资料或适当影视参考。原著人物依据来源文本；真实历史人物区分同时期资料、后世描绘和影视改编，影视外观不当作历史实证。原创角色仍查课程涉及的时代、职业和环境约束。

按实际查得内容登记来源类型、标题/作者或作品与版本、可核对位置、获得方式和具体支持的特征。记录采用、未采用和未知之处；文字资料用于研究，只有真实图片/音频/视频文件才进入模型参考槽位。

找不到可用人物参考时，登记查找范围、缺失内容和 fallback 理由，再在已知情境约束内自由设计。若有来源但外观未描述，可只补全未描述部分；不以“查过了”替代来源证据，也不要求每个角色套用影视演员脸。

定义固定识别特征，按角色适用填写眉眼、胡须、发型、年龄/体态、服装/饰品及声音。状态变化单列，年龄、伤痕、装束等改变有剧情依据。提示词引用同一 character_identifier；多人镜头登记确切身份与数量。背景人群有单独说明，额外具名或扮成同身份的人物须修复。

## 1.1 计划字段

`character_sources` 是研究来源数组，与模型输入的 `references` 分开：

| 字段 | 内容 |
|---|---|
| `source_identifier` | 稳定来源 ID |
| `source_type` | `primary_text`、`historical_material`、`screen_adaptation`、`context_research` 或 `other` |
| `title`、`locator` | 作品/版本及可核对章节、页码、时间码或 URL |
| `research_file`、`research_sha256` | 本地研究记录与真实指纹；记录注明事实/改编/补全 |

`characters` 是身份数组，无身份人物的课程可显式填空数组：

| 字段 | 内容 |
|---|---|
| `character_identifier`、`display_name`、`current_identity` | 稳定 ID、首次出场姓名和当时身份；不用尚未取得的头衔 |
| `reference_status` | `referenced` 或 `no_suitable_reference` |
| `source_identifiers` | 本角色采用的已登记来源 |
| `reference_search` | 实际查找及其结果 |
| `creative_fallback_reason` | 无合适参考时必须填写；采用参考可为 null |
| `appearance_constraints` | 来源支持的固定外观和明确的创作补全 |
| `visual_reference_identifiers` | 已登记且文件可核对的 image/video 参考；有文字参考且无图时可为空 |

每个 shot 必须有 `character_identifiers` 数组。角色在镜中稍后出现时，增加 `character_appearances`，每项含 `character_identifier` 与最终时间线上的 `first_visible_seconds`；省略该数组则默认各角色在 shot 起点可见。角色与首次可见时间必须落在本 shot 区间。

`character_introductions` 是展示数组，每项含：

- `introduction_identifier`、`character_identifier`、`timeline_identifier`、`branch_identifier`、`shot_identifier`；
- `display_name` 与 `current_identity`，与身份数组一致；
- `start_seconds`、`end_seconds`，使用最终媒体时钟；
- `render_mode=burned_in_video` 与 `placement`，注明人物对应和安全区。

每个角色在每条 timeline/branch 的首次可见位置都必须有介绍。展示从首次可见起开始，在该 shot 内结束；需要更长阅读时先调整分镜。无人物课显式空数组合法；对白的具名说话者仍登记身份。

`sound_events` 的画内对白或旁白（`on_screen=true`）必须引用已登记角色，且整个事件区间由同一 timeline/branch 的该角色可见 shot 连续覆盖；稍后入镜使用 `first_visible_seconds`。镜头切换可以接续，角色尚未出现、离镜缺口或不同分支拼接不能充当画内发声。画外对白仍登记身份，但不据声音虚构出镜或首次介绍；无人物的画外旁白可以保持空身份数组。

## 实际视频介绍

人物首次出现必须在实际视频画面内显示“姓名＋简短当时身份”。使用确定性后期排字，烘焙进成片，保证导出、静音和字幕关闭仍可见。网页附加锚点可增强对应关系，不能替代成片介绍。

时长读取项目配置或本课覆盖，再按文字、语言、出镜与阅读实测确定。标注对应唯一人物，避开眉眼、胡须等识别点、关键教具、字幕和操作安全区；桌面与手机保持可辨认。多人物同时出现时逐人核对，不靠颜色猜身份。

介绍随媒体时钟暂停、跳转和重播，自然随首次出场片段重现；不以“本次已见过”隐藏视频中的文字。章节首次直入或续学需要背景时，按 reentry policy 补本地定向，不改写首次出场定义。

## 交付证据

1. 计划校验检查人物/来源/shot 引用、画内声音与出镜区间、首次出场覆盖、时间窗与字段一致；不能由声明推断画面真实人数或文字已渲染。
2. 每条有出镜人物的成片在 `manual_reviews` 中增加两项，绑定最终视频 SHA256：
   - `character_appearance`：实际人物人数、眉眼/胡须/服装等固定特征及跨镜一致；证据记录包含所见角色和检查时间区间。
   - `character_introduction`：姓名、当时身份、人物对应、开始/中间/结束帧、关闭字幕与窄屏可读性；`introduction_identifiers` 精确覆盖本片全部介绍。
3. 记录含 `status`、`reviewer`、`bound_sha256`、`evidence_file`、`evidence_sha256`，并列 `character_identifiers`。读取实际视频/提取帧后保存证据；Agent 不伪造人类确认。

视频重排、首帧变化、改名、重渲染或影响人物的局部修复后，重新计算首次出场与本版指纹，复查受影响的介绍及连续性。沿用既有设计与最难媒体两道门，不新增人物专项审批。

## 修改本契约后的回归

运行[人物契约回归](../scripts/check_character_contract.py)。它包含来源/身份/时间窗/分支覆盖、旧版提示、文件指纹与 CLI 报告正负例，并运行合成编码媒体检查。合成审阅仅用于验证记录结构；不能充当实际人物或人类确认的证据。
