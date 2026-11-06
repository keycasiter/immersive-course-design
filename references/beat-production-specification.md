# 生产级 Beat 规格

本文件定义课程 Beat 从教学设计进入媒体、互动和网页实现前必须达到的通用粒度。它是 Skill 的可复用规范，不包含任何具体学科、历史事件、角色或素材。

## 1. Beat 的定义

Beat 是视频时间线中一个具有完整学习作用的最小生产单元：

```text
视频进入
→ 信息/对象/动作呈现
→ 学习者执行一个知识动作
→ 局部反馈或对象状态变化
→ 返回声明的视频时间
```

Beat 不是一句主题描述，也不是“在这里加一个互动”的备注。一个 Beat 不完整时，不得进入正式图片、视频或交互批量制作。

当课程采用 Imagineering × PBL 整合模式时，Beat 还必须说明它如何推进项目：

```text
driving_question_link
inquiry_action
persistent_artifact_update
feedback_or_revision_link
```

也就是说，学习者在 Beat 中获得的资料、判断、模型结果或表达，必须能更新持续作品，或明确说明为什么本 Beat 只承担体验/支架作用。没有项目贡献的 Beat 不能伪装成 PBL 项目步骤。

## 2. 必填生产字段

每个 Beat 必须有一张生产卡，至少包含：

```text
beat_id
content_contract
learning_action
video_function
timeline_window
shot_list
voice_script
interaction_contract
asset_registry
generation_constraints
acceptance
```

### `content_contract`

把内容拆成三层：

| 层 | 内容 | 要求 |
|---|---|---|
| `fact` | 可由来源支持的事实、定义、数据和规则 | 绑定来源 ID 或标记待核 |
| `interpretation` | 教学解释、因果连接、抽象概括 | 不写成来源原话或确定事实 |
| `creative` | 情境、镜头、角色动作、视觉隐喻 | 不承担事实证明责任 |

未核实的事实必须写 `FACT_VERIFY`，不能由生成模型自行补全。

### `learning_action`

必须具体描述学习者做什么，例如：

- 观察并定位对象；
- 将证据分类；
- 比较两个解释；
- 调节一个局部变量；
- 选择证据支持某个判断；
- 写出带限定条件的解释。

不能只写“理解”“思考”“参与互动”。

### `video_function`

说明为什么这段内容需要视频时间线，以及视频承担什么作用：

- 展示动作顺序；
- 呈现因果变化；
- 建立空间关系；
- 保留人物回应和停顿；
- 提供进入互动的现场上下文；
- 让互动结束后回到同一事件。

如果只需要静态信息，应改用页面资料或图示，不为了填满视频而增加 Beat。

## 3. 时间线规格

时间字段全部使用主视频的绝对秒数：

```json
{
  "cue_seconds": 42,
  "pause_seconds": 45,
  "resume_seconds": 48,
  "cue_tolerance_seconds": 0.25
}
```

必须满足：

```text
0 <= cue_seconds <= pause_seconds <= resume_seconds <= duration_seconds
```

字段语义：

- `cue_seconds`：运行时识别事件并准备互动的时间；
- `pause_seconds`：视频停止并打开互动的时间；
- `resume_seconds`：互动完成或关闭后的返回时间；
- `cue_tolerance_seconds`：识别时间误差，不是互动持续时长。

事件按 `cue_seconds` 升序排列。必需暂停窗口不得重叠。向前拖拽遇到未完成的必需事件时，回到该事件的 `pause_seconds`；回看已完成事件时不重复创建学习记录。

## 4. Shot 规格

每个 Beat 的 `shot_list` 至少拆到可以独立生成、组装和验收的粒度：

| 字段 | 要求 |
|---|---|
| `shot_id` | 在课程版本内稳定唯一 |
| `time_range` | Beat 内相对时长和最终主线位置 |
| `subject` | 画面中实际出现的对象 |
| `action` | 一个主要动作链，不写抽象情绪 |
| `camera` | 景别、位置、方向和运动 |
| `continuity_in` | 与上一镜头的状态衔接 |
| `continuity_out` | 与下一镜头或互动的状态衔接 |
| `sound` | 人声、环境声、动作声和字幕关系 |
| `reference_ids` | 角色、场景、道具或首尾帧参考 |
| `negative_constraints` | 不得出现的身份、时代、动作和文字 |

默认一个 Shot 只包含一个主要动作链。动作、声音或证据揭示不能在中间随机切断。

## 5. 旁白和对白规格

每条语音必须绑定：

```text
utterance_id
speaker_id
text
purpose
source_or_creative_status
start_condition
end_condition
visual_coverage
caption_text
```

要求：

- 先确定完整文本，再根据实际声音确定视频时序；
- 不用固定秒数强行压缩完整台词；
- 画内说话必须有对应出镜、动作和口型验收；
- 画外声必须说明其覆盖的对象或行动；
- 学习解释、角色原话和来源引语不能混写；
- 没有来源的角色原话必须改为旁白概括或标记待核。

## 6. 互动规格

每个互动必须写清：

```text
interaction_id
entry_object
learner_input
input_schema
completion_condition
feedback_rule
local_state_change
resume_seconds
close_behavior
failure_behavior
keyboard_equivalent
touch_equivalent
```

互动规则必须是确定性的。相同输入、相同课程版本和相同局部状态，应得到相同反馈。

互动默认只改变：

- 当前对象状态；
- 当前视图；
- 仿真局部变量；
- 阅读/标注位置；
- 即时反馈；
- 当前会话草稿。

互动默认不改变课程主线。需要改变主线时必须在设计确认中显式批准，并为每条路径建立独立事件、资源、目标和验收。

## 7. 资产规格

`asset_registry` 至少登记：

```text
asset_id
asset_type
beat_id
teaching_purpose
source_or_generation_tool
reference_ids
version
input_hashes
output_hash
status
acceptance
```

确定性资产和生成资产分开：

### 交给确定性工具

- 地名、日期、姓名和准确文字；
- 地图、时间线和图表；
- 公式、数据、规则和仿真结果；
- 字幕、按钮、标签和证据引用；
- 需要精确位置的热区。

### 可以交给生成工具做候选

- 无文字的环境背景；
- 不承担史实证明的氛围镜头；
- 角色远景、背影和动作参考；
- 道具材质和非关键细节；
- 已锁定首尾状态之间的动作候选。

图片使用 TRAE `GenerateImage` 或 Codex `Image gen`。视频使用 TRAE `GenerateVideo`。工具输出只能标记为候选，必须通过资产和 Beat 验收后才能进入正式组装。

## 8. 生成约束

生成提示词不是自由创作文本，而是从生产卡编译出来：

```text
教学作用
→ 主体与状态
→ 场景与时代/空间约束
→ 参考文件及其职责
→ 按顺序的动作
→ 相机与光线
→ 终止状态和接续状态
→ 负面约束
```

每次生成绑定：

```text
beat_id
shot_id
asset_id
production_card_version
reference_hashes
prompt_version
tool_identifier
tool_version
output_hash
acceptance_status
rejection_reason
```

重新生成必须记录改变了哪一个字段和为什么，不能只覆盖旧文件。

## 9. Beat 完成等级

| 等级 | 条件 |
|---|---|
| `beat_draft` | 有目标、学习动作和初步视频作用 |
| `beat_specified` | 内容、时间、互动、反馈和资产字段完整 |
| `beat_media_ready` | 史实/来源已绑定，参考、镜头、声音和生成约束完整 |
| `beat_accepted` | 媒体、互动、返回、恢复、响应式和人工审阅通过 |

课程进入 `production_complete` 前，所有必需 Beat 至少达到 `beat_media_ready`；课程进入 `functional_accepted` 前，所有必需 Beat 必须达到 `beat_accepted`。

## 10. 生产前检查

逐 Beat 检查：

1. 学习者是否有一个明确、可观察的知识动作；
2. 视频是否承担不可替代的时间、动作或情境功能；
3. 事实、解释和创作是否分开；
4. Shot 是否有进入和结束状态；
5. 旁白是否有完整文本和视觉覆盖；
6. 互动是否有确定性输入、反馈和返回；
7. 所有资产是否有稳定 ID 和版本；
8. 生成工具是否只处理适合生成的部分；
9. 失败、刷新、回看、键盘、触摸和手机行为是否明确；
10. 是否能用生产卡编译出提示词、Job 和验收项。
11. 若采用 Imagineering × PBL，是否推进了驱动问题、持续探究或持久作品，并有反馈/修订关系。

任一项缺失，Beat 只能停留在 `beat_draft` 或 `beat_specified`，不能直接生成正式媒体。
