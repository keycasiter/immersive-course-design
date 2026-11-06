# 沉浸设计取证与体验评价

本文件拥有沉浸意图映射、v2 评审包和体验测量协议。[课程评价](course-evaluation.md)负责教学与学习效果；[内容质量](content-design-quality.md)拥有 `immersion_elements` 的作用与保留决定；[呈现契约](video-presentation-contract.md)拥有时钟、背景和热区。沿用既有确认门，不另设沉浸总分或审批。

## 1. 触发与执行

新课或重大体验改稿在设计阶段执行本节；评价任务、沉浸效果声明、氛围/角色/视角/互动变化在当前有效阶段继续：

1. **确定主张和范围**：写具体体验意图、设备、入口、参与方式及版本，选择适用构念。无角色、纯观看和无连续剧情均可成立。
2. **落实到材料**：展开 `immersion-plan.json`，把意图映射到实际镜头、声音、互动和返回状态。设计尚无成片时保留 planned；媒体审阅需要当前声画与操作。
3. **逐项取证**：对适用原子逐实例审阅，独立记录定位、观察、反例与限制；需要验收使用时先执行评价者校准。结构检查与语义判断分开。
4. **完整走课**：按 §5 检查实际全程、累计负担、兑现与恢复。局部通过不能推导全程通过。
5. **试学与比较**：按 §6—7 准备并执行授权的真实测量。准备完成只报告协议就绪；实际学生数据才能支持实际体验结论。
6. **分别报告**：工程、体验评审、学生感受、学习表现分列。未执行、适用性未知、矛盾、待复核逐项列出，不求均分。

完成条件：授权范围内每个适用实例有当前证据或明确缺口；结论绑定版本、条件、观察范围和责任人。试学未授权或未执行时继续完成可审材料，保留“实际体验未评估”。

## 2. 从意图到可观察判据

使用随包[原子目录](../assets/immersion-evaluation-criteria.v2.json)。它收录 M13 的 15 项、M18-A08/A09 和完整旅程 M18-C01-v2；保留原标识，属于沉浸分支子集，既不是全部视频评测也不与旧八维分数等价。按每项的适用性、判据、正反例与所需证据展开实例。

| 设计判断 | 必须体现的声画/交互决定 | 审阅证据 | 真实体验证据 |
|---|---|---|---|
| 进入与定向 | 当前对象、处境、视角/权限和第一步；入口前后共享线索 | 入口前中后、原句、第一屏及零背景走读 | 能否复述处境；何时开始迷失 |
| 空间关系与在场 | 视角、尺度、对象位置、声源位置连续；窄屏仍可读 | 相邻镜头、整页播放、空间标注、声音 | 适用主观报告及具体时刻；二维空间可读与头显身体在场分开 |
| 事件可信 | 已建立规则、条件、变化与后果一致；事实/模型/创作边界明确 | 前因和结果、规则来源、两个有效输入 | 哪处说得通/困惑、原因；写实美术不代替可信 |
| 好奇与叙事投入 | 待解释的信息具体；兑现与出口回连它；无叙事按关注对象评价 | 期待和揭示两个区间、全程出口 | 想继续了解什么、何时失去兴趣，允许“没有” |
| 能动感 | 承诺的可控范围、输入和可理解后果对应 | 两个不同输入、反馈/修订和返回 | 怎样理解自己改变了什么；无控制承诺记不适用 |
| 情绪、注意与节奏 | 内容与预期情绪相关；主对象优先；留出观察/思考空间 | 实际听看、字幕开启、最长材料与后半段 | 实际感受、漏看、负担、疲劳/不适、退出 |

`immersion-plan.json` 使用[模板](../assets/immersion-plan.template.json)：

- `schema_version=2.0`、`course_identifier`、`course_version`、`scope`（complete_course/local_revision）、`scope_description`、当前随包文件的 `catalog_sha256/rubric_sha256`。
- `coverage` 对目录所有 18 项各写一条：`atom_identifier`、`applicability`（applicable/not_applicable_with_reason/not_evaluated）、`applicability_reason`、`unit_identifiers`。局部修改按范围声明不适用；尚未判断保持 not_evaluated，不能当作排除完成。
- complete_course 不能排除完整旅程；尚未走课可以登记 not_evaluated。模板的入口实例只是字段脚手架，须替换占位并展开全部适用实例。
- `units` 每项是一个判定实例：`identifier/atom_identifier/evaluation_stage/experience_intent/construct/element_identifiers/design_decisions/scene_identifiers/beat_identifiers/shot_identifiers/asset_identifiers/observable_success/observable_failure/required_routes/comparison_plan`。标识列表均显式提供；不涉及镜头或元素可为空，场景/Beat 至少有一个。design_decisions 和 required_routes 至少各一条；comparison_plan 写移除/静态/低动态比较的差异与控制，不需要时写理由。
- `evaluation_stage` 取 design/media_review/controlled_runtime/learner_trial。learner 原子只在 learner_trial 下记录实际体验，未执行仍可建立计划；完整旅程在 controlled_runtime 或 learner_trial 下分别表示专家走课或真实试学。
- `construct` 取 orientation/spatial_presence/event_credibility/narrative_engagement/agency/emotion/attention_pacing/continuity/background_increment/full_journey。同一原子可展开不同构念实例；学生各构念分别记录。

同一判据在不同入口、转场、关键事件、互动或恢复路线发生时分别展开，引用既有场景/Beat/shot/资产标识。每个保留元素都有可定位的体验作用与删除损失；允许教学证据相同而体验连续性有增量。新增标识只用于评审实例，不改变 blueprint/manifest schema。

## 3. 正式评审包及机械校验

使用[评审包模板](../assets/immersion-review-packet.template.json)和[量规](../assets/immersion-review-rubric.v2.json)：

```bash
python3 scripts/validate_immersion_review.py immersion-review-packet.json --output immersion-review-validation.json
```

所有路径相对评审包目录解析。随包目录和量规的实际字节指纹必须匹配；旧八维记录保留旧通道，不换算或默认为 v2 已评。占位模板须展开后才校验。

| 包字段 | 内容与责任 |
|---|---|
| `schema_version/course_identifier/course_version` | 2.0 及本课本版，与 plan 一致 |
| `purpose` | diagnostic/acceptance；诊断自审不充当独立验收 |
| `plan` | `{path,sha256}`，读取实际 plan，不只相信记录里的覆盖声明 |
| `catalog_sha256/rubric_sha256` | 当前随包文件的实际指纹 |
| `artifacts` | `{identifier,path,sha256,kind}`；kind 为 video/audio/document/image/runtime_log/learner_record；媒体另有 duration_seconds，用 ffprobe 读实际时长核对 |
| `calibrations` | 见 §4；完成校准需要当前量规与实际记录 |
| `records` | 稳定 identifier/unit_identifier，及下述字段；不同审阅者可分别记录同一实例 |

记录包括 `atom_identifier/catalog_sha256/rubric_sha256/evaluation_stage/applicability/applicability_reason/score/reviewer_role/reviewer_identifier/artifact_sha256/time_range_or_locator/observed_behavior/criterion_rationale/limitation_or_counterexample`，另有 `status/finding/evidence_references/observed_routes/calibration_identifier`：

- applicability 与 plan 一致。适用实例尚无证据用 status/finding=not_evaluated、score=null；分歧未解决用 review_pending/null。实际矛盾才能记 contradicted；缺证据不记 0。
- reviewer_role 取 author_self_review/human_review/model_judge/learner_observer，来源如实登记；文件与指纹校验不认证身份、签字或实测真实性。
- status=observed 必须有观察、判据解释、限制、当前证据和观察路线。语义 finding 为 contradicted/weak/established，按量规给 0–4 描述；learner 或 full_journey 保持 score=null，finding 为 supported_in_observed_conditions/not_supported/inconclusive。学生报告和学习表现分别解释。
- evidence_references 为 `{artifact_identifier,locator}`；locator 是 time_range（start_seconds/end_seconds，半开区间）、line_range（start_line/end_line，1 起算）或 json_pointer（value，RFC 6901）。媒体必须用时段；非媒体定位必须能从当前文本或 JSON 读到。artifact_sha256/time_range_or_locator 对应第一条证据；前后片段和不同输入保存在列表。
- 声音判据提供音频或视频；media_review 提供当前音频/视频/图像/实际操作记录，不能仅用脚本；实际体验提供 learner_record 且由 learner_observer 记录，完整走课提供 runtime_log 或 learner_record。
- 0 分与 contradicted、1 分与 weak、2–4 分与 established 对齐。3 分至少有两个不同前后证据定位；4 分还须覆盖实例全部 required_routes。机械条件只检查记录，不能证明内容真的成立。
- observed_routes 是实际覆盖路线，必须来自实例 required_routes；每位审阅者未覆盖的路线保留缺口。主观评分不能补齐路线。

输出 `record_contract_status`、结构错误、coverage 的适用性未知、缺记录、未评、待复核、矛盾/薄弱、不具备验收使用条件的记录，以及每实例路线缺口。退出码 0 只表示记录契约有效，允许诚实的不完整包；`review_coverage_complete` 另表示适用实例均有观察且路线齐全。两者都不表示沉浸效果成立。校验器不计算沉浸总分、不签验收、不计算学生效果。

## 4. 审阅校准与判定责任

先选同一原子的成对材料：保留/移除、规则一致/矛盾、精致但位置漂移/克制但定位清楚、合法无角色与无控制承诺路线、局部连续但期待未兑现。实际材料由本课或独立练习集提供，不把样例类型写成已完成金标。

评价者先独立记录定位与理由，再比较分歧、修改解释，在未参与规则调试的材料上复核。按用途/风险确定复评比例，保留原始判断而非只留协商后的分数。作者自评与模型建议分别注明。

calibrations 每条含 `identifier/reviewer_identifier/reviewer_role/status/catalog_sha256/rubric_sha256/evidence_references/paired_specimen_references/independent_example_references/disagreement_resolution/limitations`。status 为 pending/completed；completed 需校准原始记录、至少两条不同配对材料和独立复核引用。模型用于验收还需 authorization_reference 和独立保留集证据，沿用本课 evaluation plan 的启用决定，不由模型自证。未完成可诊断，列为验收使用待复核。学生原始报告由 learner_observer 保存；工具适配与解释校准另按试学协议处理，不套专家 0–4 分。

2 分仅表示当前样本有明确成立实例；若作临时设计筛查，预先声明用途与限制。没有经验证的通用沉浸合格线。具备验收使用条件后，实际审阅者对照本课 observable_success/observable_failure 和观察范围写成立、需修订或证据不足，并引用记录；遇到必需连续性、可达性或运行硬失败，按原 owner 阻断。学生体验结论需真实测量，不能由专家分数升级。复评不以平均抵消直接矛盾；修订后更新指纹并重评受影响实例。

## 5. 完整旅程验收

M18-C01-v2 单列实例：登记真实入口→观察/示范→引导→独立→修订→迁移→收束的本课对应位置。按实际路线合并或说明不适用阶段，不增加固定互动配额。

执行一次连续正常走课，并覆盖适用的深链接/恢复、错误/求助/修订、静音/低动态/等价路径。保存入口到收束的原始轨迹（版本、事件、动作、媒体时间、状态、困难）、整页画面与必要声音；局部截图只能定位问题。重点观察：

- 开场承诺是否到后半段仍成立且最终兑现；
- 对象、空间、规则、声音、工作面和个人记录是否接回同一状态；
- 重复中断、阅读/输入、等候与新信息是否累积负担；
- 独立表现是否被提示泄露，帮助撤除后能否开始；
- 长段落疲劳、退出、迷失与重新定向。

专家走课只能给完整体验设计判断。要求真实学生完整体验时另执行 learner_trial 实例并关联个人表现。结果、失败时刻、未覆盖路线分别列出，不从 M13 均分推出。

## 6. 真实学生的体验测量

在 evaluation-plan.md 使用[试学模板](../assets/immersion-learner-trial.template.md)。按主张选构念和工具，不默认成人问卷适用小学生或二维网页。

| 必填 | 要求 |
|---|---|
| 主问题与构念 | 空间在场、事件可信、叙事投入、能动感分列；注意/迷失、负担/不适保存。无叙事/控制承诺写适用性理由 |
| 工具出处与适配 | 名称、作者/年份、原文链接/DOI、原人群/媒介、原题项/计分位置、使用条件；核对中文、年龄、媒介与本课。改写/抽题登记变化与认知访谈实际结果 |
| 工具选择路径 | 空间在场可检索 MEC-SPQ/IPQ 等候选，叙事投入可检索 Narrative Engagement Scale 等候选；只是检索方向，执行者须取原文核对。本 Skill 不提供已验证中文儿童量表 |
| 测量时机 | 先记录先修/设备，正常体验尽量连续，段后或结课回溯具体时刻；体验反馈、独立任务与延后保持的时间分列；边想边说单列条件 |
| 原始回答 | 题项/访谈版本、原回答、否定、说不清、不适用、跳答/退出与原因；无响应不填零，不只保留完成者 |
| 退出与不适 | 开始前说明可停/跳过/休息；不适时停止刺激，保存时刻/动作、已完成范围和恢复方式，不强迫继续 |
| 分析与解释 | 分构念报样本、分母、分布/原话、事件、缺失和不确定性；未经适配验证仅描述探索性观察，不套原量表阈值 |

探索性回溯可问“哪一刻开始知道自己在看什么？”“哪个变化说得通，哪个让你困惑？”“还想知道什么？”“觉得自己改变了什么？”“哪里太快、费力或不舒服？”先检查措辞理解，提供没有/说不清/不适用和跳过。这些是探索性问题，不是验证量表；预期情绪、作者判断和实际回答分开。

默认脱敏编号与最小化记录，身份/上传按既有规则。模拟学习者、Agent 走读或生成回答只用于发现设计问题，不能填 actual learner evidence。

## 7. 背景与体验增量比较

M18-A09 只在声明动态背景改善时执行；设计阶段移除/低动态走读不冒称学生效果研究。

1. 写比较问题和版本差异。固定视频、声音、字幕、任务、帮助、设备、亮度/尺寸和测量条件；当前构建/媒体分别绑定。
2. 按问题选分组或顺序平衡；同一学生重复同内容的练习/熟悉/新奇影响单列。保存实际分配、顺序、暴露时长、基线和偏离，不只写随机标签。
3. 分别记录氛围/投入、必要信息可读、负担/不适和学习。更吸引但更难观察时保留两项发现，不平均抵消。
4. 预先写指标、工具、样本依据、缺失/退出处理和分析。小样本描述与因果归因分开，未执行保持 not_evaluated。

当前背景工程评价走呈现 contract 1.0 的 validate_video_presentation.py/check_video_presentation.py 及实际浏览器采集。旧 M17 顶层 cues、首 cue 混合进度与旧 runner 不代表新嵌套 atmosphere.cues 已验收；适配边界由呈现 owner 说明。
