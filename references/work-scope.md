# 工作范围、交付形态与产物矩阵

本文件是 `scope_type × learner_delivery_type × experience_profile` 派发的唯一权威。局部任务不能推进父课程状态；方法维护不使用课程清单。

## 范围与终点

| `scope_type` | 基础产物与检查 | 最大默认终点 |
|---|---|---|
| `full_course` | 先建立来源约束的必需内容清单，再证明目标、知识、场景与 Beat 对清单的完整覆盖；交付本形态的完整设计、蓝图、核对与清单 | 用户授权的实际阶段 |
| `local_design` | 所选目标的完整教学闭环；covered/excluded；父范围与影响分析 | `design_confirmed` |
| `media_assets` | asset manifest、Job、实际文件、版本、治理、等价路径与验收 | `assets_accepted`；父状态不变 |
| `illustrative_prototype` | 设计契约、源文件、静态/运行审阅；模拟素材明确标注 | `design_draft` |
| `course_implementation` | 已确认设计与代表性闭环、实现、正式文件及适用功能验收 | `functional_accepted` |

基础工作文件不按固定数量表述。完整设计可能需要 `design-outline.md`、`course-design.md`、`evaluation-plan.md`、`course-blueprint.json`、`verification.md` 和 `production-manifest.json`；其余按下表增加。它们是按本课决策生成的设计草稿或审阅记录，不是复制即合适的正式产物。没有真实内容、运行证据或适用确认时，允许只保留纲要、决策记录和风险清单。

## 学习者交付形态

| `learner_delivery_type` | 增加的设计/生产产物 | 代表性闭环 | 功能验收 |
|---|---|---|---|
| `interactive_web` | `page-design.md`；实现时增加运行入口；按profile增加视频参与/event map或空间学习计划与runtime | 当前主媒体/对象→阅读/仿真/空间操作→可见后果/反馈→修订与返回恢复 | 浏览器正常/错误/求助/重试/回看/恢复、键盘/触摸、桌面/手机、媒体准入和无障碍等价 |
| `linear_media` | 媒体计划、时间线、字幕/文本等价、Job 与正式文件 | 最难内容、声音、画面和导航片段 | 完整播放、导航、字幕/文本等价、音画与内容连续性 |
| `facilitated_instruction` | 主持指南、学习者材料、实施脚本、评价与恢复说明 | 代表性教学实施或完整彩排 | 完整材料走读、主持人交接、学习者产出、帮助撤除和恢复 |
| `print_or_document` | 完整文档、版式/替代格式、跳转与答案/反馈边界 | 最难章节和任务的完整材料走读 | 顺序/跳转、可读性、替代格式、独立完成与反馈条件 |

对 `interactive_web + video_led_web`，上述产物还必须包含：

- `clarification-intake.md`：前置需求澄清及决定记录；
- `experience-blueprint.md`：逐 Beat 的镜头、声音、特殊帧、热区、互动状态和返回状态；
- `storyboard.md` 或 `storyboard/`：可评审的逐镜头故事板；
- `interaction-visual-spec.md`：互动点的入口、第一屏、进行中、反馈、修订和返回状态；
- `video-event-map.json`：正式实现时的媒体时钟事件表；设计阶段可以是 `planned`，但必须提前定义字段和事件边界。

如果只交付文字目标、知识组织和教学流程，范围应派发为 `local_design` 或 `illustrative_prototype`，不得把它命名为完整的视频课程设计。未制作媒体可以是 `planned`，但其可感知契约不能缺失。

设计与代表性闭环两道人类门对四种形态都保留；完整课程另须独立澄清/Demo 门禁，执行字段由[生产清单](production-manifest.md)拥有。兼容状态名 `media_sample_confirmed` 在后两类中表示“代表性交付闭环确认”，不要求伪造媒体。

## 完整课程范围门

`full_course` 不是“当前已经写出的场景集合”，也不是“若干代表性 Beat”。在写场景前，必须先在课程蓝图的 `scope_coverage` 中建立：

1. `required_content_inventory`：从用户要求、指定来源和明确深度中拆出的必需内容项。每项只承载一个可教、可练或可综合的概念、事件、过程、关系或判断边界；不能用“主题概览”“主要内容”等伞状条目合并多个独立要求。
2. `coverage_map`：每项必需内容实际由哪些目标、知识单元、场景和 Beat 承担，以及它在课程中承担 `orientation`、`instruction`、`guided_practice`、`independent_application` 或 `synthesis` 中的哪些功能。
3. `excluded_content`：经明确范围决定排除的内容及理由。排除项不是必需项，不能用于掩盖未完成内容。
4. `deferred_content`：完整设计和完整 Demo 必须为空。正式视频本体不属于内容延期，单独走视频差额契约。

完整性不使用固定 Beat 数量判断。短小目标可以有少量 Beat，复杂主题必须随必需内容清单展开。校验器只能证明声明的清单被覆盖；设计审阅仍须核对清单是否忠实覆盖用户要求和来源范围，不能把结构通过写成语义完整。

`full_course` 联合校验必须启用课程蓝图的完整范围检查。缺少必需内容清单、必需项没有映射、目标或知识单元未被内容项覆盖、必需场景/Beat 没有归属、或存在延期内容时，不得声明完整课程。

## 完整 Demo 的视频唯一差额

对 `full_course + interactive_web + video_led_web + interaction_complete_prototype`，Demo 是除正式视频本体外的最终学生端成品，不是代表性抽样。生产清单必须声明 `demo_completion.completion_policy=video_only_delta`，并满足：

- 全部课程内容、场景、Beat、字幕、交互、反馈、帮助、修订、进度、恢复、响应式和无障碍路径已完成；
- 所有必需非视频正式资产已经验收；分镜替代资产本身也已经验收；
- 唯一允许延期的工作类型是 `formal_video_generation`、`video_runtime_binding` 和 `post_video_integration_verification`；
- 每个延期项只能引用正式 `linear_video` 资产；
- 已声明正式视频替换时必须保持不变的内容、布局、交互、反馈、状态和无障碍契约；
- 正式视频接入后仍须执行媒体时钟、热点时机、字幕同步、返回状态、响应式和无障碍回归。

存在未完成课程内容、页面、交互、反馈、非视频资产或浏览器闭环时，终点仍是 `design_draft`，不能使用 `interaction_complete_prototype`。

## Profile 工作文件脚手架派发

`experience_profile`是工作文件脚手架的唯一派发字段。interactive_web按目标选择以下正式路线，不按媒体数量或沉浸外观判定：

- `video_led_web`：使用 `assets/video-led-course-page.template.html`、`assets/course-page.css`、`assets/video-led-course-page.css`；但必须先写出视频时间线、事件、互动表面和验收范围。
- `spatial_native_web`：按[空间学习生产](spatial-learning-production.md)及[场景契约](spatial-learning-contract.md)以实时教具/图解为主舞台，增加spatial-learning-plan与scene_state运行交付。不要求假视频、视频模板或GLB；保留任务/反馈的可访问语义。
- `hybrid_web`：同时包含视频与原生空间教学，逐场指定主媒体、时钟所有者、进入/返回检查点；真实视频部分执行视频契约，空间部分执行场景契约。
- 其他网页profile按其已确认形态执行，不自动继承这三条路线的特定规则。
- 非网页 delivery：不生成 HTML 占位。

- 项目 profile 只能覆盖工具、语言与环境配置，不能改变以上派发。脚手架实例默认标记为 `design_draft`；若页面只是静态示意，使用 `static_design_prototype` 作为展示标签，不得把它写成 `interaction_complete_prototype`。只有完整非视频闭环通过生产清单和浏览器证据后，才允许使用 `interaction_complete_prototype`。

## 原生空间与混合课程的完整交付

spatial_native_web与hybrid_web同样保留完整内容、澄清、内容审阅、设计、Demo及最难代表性闭环门禁。其Demo要覆盖全部必需知识动作、错误/帮助/修订、状态恢复、桌面/手机和等价路径；不借video_only_delta延期必需3D、规则、非视频资产或交互。无正式视频待制作时，延期项为空，达到正式准出仍须逐资产和功能验收。

空间课程的体验蓝图、分镜和页面追踪保留同一Beat/目标/任务，只把主媒体事件换成对象/场景状态，不强制制作视频时码或生成任务。设计阶段交可审规格，正式实现交真实运行与当前文件证据；旧课不自动迁移。

## 局部范围与继承

`work_scope` 必须包含 `scope_identifier`、`description`、`endpoint`、`learner_delivery_type`、covered/excluded 目标与资产，以及结构化 `inherited_confirmations`。

每条继承记录包含父确认 ID、scope ID、subject version、确认内容 SHA256 和父清单 SHA256。校验分两层：

1. 声明结构检查：字段、类型和指纹格式完整。
2. 继承有效性检查：解析 `parent_manifest_reference`，确认记录和 scope 实际存在、版本/哈希匹配、确认仍 active、父清单文件未变化。

只通过第一层的继承只能保留为草稿。正式实现和资产准出必须通过第二层。父标识使用独立引用，不冒用整课完成状态；依赖变化创建 versioned scope，不重写旧 scope 的依赖。

局部蓝图描述所选目标的完整教学闭环。独立小样提供与审阅范围相称的最小背景；只有运行入口可验证此前内容已呈现并提供本地回顾时，才使用 embedded/resumed。纯素材不额外制作课程开场。
