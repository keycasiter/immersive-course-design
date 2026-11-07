# 课程设计与生产阶段参考

本文件保留课程各阶段的执行要求，按[执行与持续落盘](references/execution-flow.md)只读取当前阶段。主入口 `SKILL.md` 负责派发；字段与详细规则由[契约归属表](references/contract-ownership.md)指定的文件单独拥有。

新课和重大改稿强制先经过[课程前置澄清与递进卡点](references/clarification-gate.md)。用户输入未完成澄清确认时，只能做输入整理、来源核实和既有产物盘点；不得制作 Demo。Demo 未完成独立验收时，不得进入正式成品生产。

## 1. 先派发本轮任务

从用户当前要求、已确认决定和已有产物确定分支。已授权的可逆工作继续执行；只为改变目标、权限或不可逆成本的未决项澄清。用户要求优先于本 Skill 默认值。

### `video_led_web` 全局硬约束

只要课程的 `experience_profile` 是 `video_led_web`，先把页面编译成**视频主舞台**，再设计任何互动。播放态只有视频承担主内容；暂停态只在同一视频事件上打开一个当前工作面；完成或关闭后收起工作面并回到原视频事件。

执行时必须满足：

- 页面根舞台只有一个媒体主舞台；课程标题、目录、侧栏、证据卡、进度面板、结果卡和页脚不能常驻。
- 控制、章节、字幕、对象入口和互动工作面按事件按需显示；不能用常驻课程工作台承载导航或教学记录。
- 互动必须先暂停视频，保留当前画面对象/人物/资料锚点；一次只显示一个当前判断和一个主动作。
- 播放态、暂停态、反馈态、返回态分别通过 `video_led_visual_gate`；任一状态出现未声明的并行面板或装饰性导航，直接阻断交付。
- 生成页面前必须使用视频主导模板和 `video-surface-contract.md`；通用课程卡片、三栏布局和 Dashboard 布局不得作为 `video_led_web` 起始结构。

这不是视觉偏好，而是路由条件。页面结构检查、视频舞台回归和视觉 Gate 未通过时，不能称为 `video_led_web` 页面，也不能推进 Demo 或功能课程终点。

| 当前任务 | 执行入口 | 本轮完成条件 |
|---|---|---|
| 优化或复核 Skill、Agent 路由、规则、模板或校验 | [Skill 维护](references/skill-maintenance.md)，同时使用 writing-for-agents；用户指定 skill-creator 时按其 Update/Validate 检查 | 已授权维护实际更新启用目录、同步模板与校验并通过回归；仅审查则交付可定位的问题与证据 |
| 新课、完整课程、重大教学改稿 | 下方课程流程，从范围与设计入口开始 | 达到已授权 endpoint，保存对应版本和验收证据 |
| 局部页面、媒体、台词或互动修改 | [工作范围](references/work-scope.md)，再进入对应专项 | 修改覆盖授权范围，受影响的契约、确认指纹和验收更新 |
| 原型 / Demo | [工作范围](references/work-scope.md)、[知识载体与 Demo](references/knowledge-surface-and-demo-contract.md) | 完整非视频体验达到学生端水平，剩余视频工作逐项登记 |
| 启动、验收、试学或效果评价 | [实现落地](references/implementation-playbook.md)、[课程评价](references/course-evaluation.md) | 保存实际执行证据；未执行项准确标明 |

Skill 维护分支完整执行其入口后交付，在此退出课程流程。具体课程只作为隔离验证样例；把反馈转成通用触发条件、权威规则、模板字段和可检查行为。

**本步完成**：分支、实际修改目标、授权范围与交付终点明确；后续只加载该分支所需材料。

课程流程按[交付验收契约](references/production-manifest.md)确定本轮路径。课程内容质量门先于媒体、页面和正式生产；每步完成后核对终点：已达终点则交付；仍有已授权工作则继续；确认缺失时完成可审材料并停在相应门。已有产物从最早失效或未完成阶段恢复。

### 课程设计主链

新课、完整课程和重大教学改稿固定按下列顺序推进：

```text
学习情境与内容边界
→ 知识点难点与学科教学选择
→ 内容候选发散
→ 学习目标与成功证据
→ 教学序列：示范/引导/独立/修订/迁移
→ Imagineering 体验与 PBL 适配
→ 媒体、空间、互动与页面
→ 实现、试学与验收
```

不能从课程标题直接生成剧情、视频、角色或页面。候选发散、质量评分和 Imagineering 增量由[内容设计质量与 Imagineering 路由](references/content-design-quality.md)负责；未通过 `content_approved` 不得进入 `design_confirmed`。

### 交付终点门（实现前必须完成）

先把用户用词编译成一个正式 `delivery_endpoint`，再创建页面或媒体：

对“做一门课”“做 Demo”“做页面”“做成品”等新课/重大改稿请求，先读取并执行[课程前置澄清与递进卡点](references/clarification-gate.md)。`clarification_confirmed` 是所有 Demo/页面制作的前置条件；`demo_accepted` 是所有正式成品生产的前置条件。

| 用户意图 | 正式终点 | 允许交付 |
|---|---|---|
| 设计稿、课程方案、静态示意、线框或只要结构 | `design_draft` | 设计文件；可附带静态预览，但必须标为 `static_design_prototype` |
| Demo、原型、学生端可体验、可运行课程 | `interaction_complete_prototype` | 除正式视频本体外，非视频部分达到最终学生端水平 |
| 视频小样或代表性媒体闭环 | `media_sample` | 已确认设计范围内的代表性媒体和闭环证据 |

当用户没有明确终点但说“做一个课程”时，先依据是否要求学生端可体验来判断；无法判断时保守停在 `design_draft`，不要自行把静态页面升级为完整 Demo。

选择 `interaction_complete_prototype` 后，**先读取**[内容设计质量与 Imagineering 路由](references/content-design-quality.md)、[知识载体与 Demo 契约](references/knowledge-surface-and-demo-contract.md)、[工作范围](references/work-scope.md)、[生产清单](references/production-manifest.md)和[前端原型契约](references/frontend-prototype-contract.md)，并在实现前建立：

- 完整 `required_content_inventory` 与 `coverage_map`；
- 按内容质量 owner 为每个核心目标展开候选、评分、淘汰理由和 `selected_candidate_ids`；
- `experience_design_mode`（`imagineering_only`、`project_extension`、`pbl_bounded` 或 `pbl_full`）及其适配理由；
- 每个保留的 Imagineering 元素的 `immersion_increment` 和删除损失；
- 每个知识目标的 `knowledge-surface-matrix`；
- manifest 中的 `demo_completion.completion_policy=video_only_delta`；
- 非视频资产清单、运行入口、浏览器验收范围和证据文件。
- `video_led_visual_gate`：按播放态、暂停态、互动完成态登记主舞台、允许的辅助层和装饰元素准出条件。

**硬阻断**：只要以下任一项未完成，就不能使用 `interaction_complete_prototype` 或“完整 Demo/学生端成品”表述，也不能把 representative sample 当作全课交付：

1. 课程内容、场景、Beat、知识动作和独立应用未全量覆盖；
2. 页面、反馈、帮助、修订、进度、刷新/回看恢复、响应式或无障碍路径未完成；
3. 任一必需非视频正式资产或分镜替代资产未验收；
4. 缺少错误、求助、修订、关闭/返回状态；
5. 缺少桌面端和窄屏浏览器证据；
6. `validate_course.py`、`validate_production.py --joint` 或适用的页面/运行时检查未通过。

未满足硬阻断时，主动将终点降级为 `design_draft`，在交付中明确写 `static_design_prototype` 和缺口；不要把“页面能打开”“脚本语法通过”当作 Demo 完成证据。

| 本轮终点或任务 | 执行路径 |
|---|---|
| 设计草稿或设计确认 | §2—5，完成授权的设计检查或确认后交付 |
| 完整交互原型 | §2—5、§6 适用页面部分、§7 非视频实现、§8 适用功能检查；正式视频延期按 Demo 契约登记 |
| 代表性媒体小样 | 已确认设计 → §6 代表性闭环及适用确认 → 交付小样 |
| 全量制作完成 | 澄清、设计、Demo 与代表性闭环均已确认 → §7 组装及逐资产验收后交付；功能检查仍按本轮授权执行 |
| 功能课程 | 已确认设计 → §6 → §7 → §8 功能验收后交付 |
| 试学准备、实际试学或效果评价 | 从已有有效阶段进入 §8，只执行本轮授权的准备、试学或评价 |
| 局部修改或单纯运行验收 | 按工作范围进入对应专项，完成影响分析与适用复验后交付 |

## 2. 课程范围与设计入口

课程任务读取[工作范围](references/work-scope.md)、[生产清单](references/production-manifest.md)和[流程状态](references/orchestration-and-status.md)。按其定义分别记录范围、学习者交付形态、体验配置、媒体模式、交付终点与验收范围。

本 Skill 的课程路线默认 `video_led_web`：视频事件承担推进、回看和恢复，阅读、仿真、确定性教具与空间视图附着在当前事件。明确要求其他形态时记录适用性并改派合适能力。项目工具与语言默认只从[项目生产配置](references/project-production-profile.md)读取。

新课和重大改稿读取[设计者输入](references/designer-intake-and-clarification.md)和[课程前置澄清与递进卡点](references/clarification-gate.md)，形成 `clarification-intake.md` 与稳定决定记录。涵盖学习者起点、语言、设备、无障碍、独立表现、内容来源与深度、用途、参与方式、媒体与预算约束。先提取已知事项，再逐项处理会改变方案的缺口；假设可以登记，但不能关闭澄清卡点或进入 Demo 制作。

完整课先建立来源约束的必需内容清单，再生成内容候选并完成内容质量审查，之后才映射目标、知识、场景和 Beat；已生成片段不能反向缩小完整课程范围。候选发散、跨学科/跨场景参考、质量评分和体验增量检查读取[内容设计质量与 Imagineering 路由](references/content-design-quality.md)。

用户提供或继承图片、音频、视频时，先执行[输入媒体实检](references/source-media-admission.md)，再据其内容形成来源判断与制作计划；真正无输入和输入检查失败分别记录。

**本步完成**：全部必需内容有来源和覆盖位置；所有会改变方案的决定已由用户确认，或已明确停在澄清卡点；未确认的假设不能进入 Demo。

## 3. 从知识推导体验与教学

首轮已读的[学科教学与体验选择](references/subject-pedagogy.md)及适用知识类型继续作为教法依据；未覆盖知识点按该 owner 定点补查。必读[内容设计质量与 Imagineering 路由](references/content-design-quality.md)、[知识到体验](references/knowledge-to-immersive-experience.md)、[知识组织](references/knowledge-organization.md)、[教学设计](references/instructional-design.md)、[学科交互](references/subject-interaction-guidance.md)与[课程评价](references/course-evaluation.md)。

固定推导链，保持课程方案开放：

`目标与未知点 → 知识对象、关系与边界 → 学科难点、教学机制与表征桥梁 → 学习者动作 → 证据 → 体验关键时刻 → 承载世界/事务 → 视角与权限 → 视频事件 → 互动、反馈、修订与返回 → 新条件下独立应用`

至少比较两个结构不同的承载候选。先选择 `experience_design_mode`，再设计世界、人物、视角、技术与互动；Imagineering 负责体验与生产层，PBL 仅在筛分适配时启用。每项必需目标落实适当讲解/示范、引导练习、帮助撤除、针对性反馈、补救再做与独立应用。

任务内容执行教学设计中的“深度检查”：对理解、解释、机制与迁移目标，必须使用关系、条件或证据完成判断；按需采用比较、删改、反例、预测或证据边界。简单识别目标保留合理的识别任务。界面精简保留关键推理，不按固定互动数量或题型配额设计。

Imagineering 先读取[内容设计质量与 Imagineering 路由](references/content-design-quality.md)和[Imagineering 思想的课程转译](references/imagineering-for-learning.md)，分别登记学习作用和体验作用。随后读取[适配筛分](references/pbl-fit-screening.md)判断是否启用 PBL；只有适配时安排驱动问题、持续探究、持久作品、受众、批评和修订。短时沉浸互动可使用 `imagineering_only`，不自动声明 PBL。

新课或重大体验改稿必读[沉浸设计取证与体验评价](references/immersion-evaluation.md)，把体验意图、适用构念、声画/互动决定、场景与素材、正反判据和待验证路线关联到 `immersion-plan.json`。体验作用可独立成立；当前尚无成片或学生观察的项目保留计划状态。

**本步完成**：每个必需目标可追溯到教学、学习者实际动作、判定依据与独立应用；内容候选已通过质量门；体验模式、Imagineering 增量和 PBL 适配已记录；通过派生、进入、教学和非复刻检查。

## 4. 编译可制作的体验

先读[情境进入](references/situated-entry-and-world-transition.md)、[课程开场](references/course-opening.md)、[叙事尺度](references/narrative-scale-and-perspective.md)与[学习者语言](references/experience-framing-and-learner-language.md)。

开场为实际入口路径提供现实锚点、诱发事件、过渡、身份、首个有后果的行动和持续世界。背景事实由信息单元保存，入口设计只引用；主动等价路径有独立设计与验收。开场的故事承诺必须来自已通过内容质量审查的问题、对象或作品，不能先造世界再寻找知识。

新课、完整设计和重大教学改稿必读[设计颗粒度](references/design-detail-standard.md)，局部设计按所选范围核对。读[体验蓝图](references/experience-blueprint.md)、[故事板与交互状态](references/storyboard-and-interaction-spec.md)和[Beat 生产卡](references/beat-production-specification.md)。完整呈现镜头/帧、逐句台词、必要对象、暂停点、互动第一屏、操作、反馈、修订、帮助和返回状态。未制作媒体标为 planned/prototype，仍提供可感知设计。

编写分镜时必读[剧情—教学—分镜](references/narrative-storyboard-integration.md)，在制作提示词之前按[分镜独立审阅](references/storyboard-review.md)实际审正文并保存当前范围记录。仅列场景功能或因果标签不能完成这一步。

按[参与设计](references/scene-participation-design.md)、[载体实现矩阵](references/interaction-surface-implementation-matrix.md)和[课程契约](references/course-contract.md)选择知识动作、最小技术、确定性反馈与无障碍等价。设计或调整互动布局、材料阅读和操作文案时，必读[交互与操作负担](references/interaction-and-atmosphere.md)。热区是入口，知识动作在当前对象上发生。

人物参与时，**在编写人物形象和生产提示词前**读取[人物参考与首次出场](references/character-reference-and-introduction.md)；研究来源、固定特征、出镜清单和介绍时间窗进入视频计划。来源事实、推理与创作分别登记。

**本步完成**：所有必需 Beat 达到可制作状态；设计者与制作人员只读产物即可复原一次体验，稳定标识跨文件一致。

## 5. 设计检查与第一道确认门

运行适用结构检查，审阅内容质量候选、目标覆盖、教学深度、来源、台词、开场、互动状态和可制作性。结构通过只证明结构；内容审查必须另有 `content_review` 状态和学科/教师证据。

设计确认绑定实际版本、范围与指纹。Agent 和脚本不能代签人类确认。已有授权和确认按[流程状态](references/orchestration-and-status.md)复用；仅对受影响的确认范围重新处理。

**本步完成**：实际设计已按第一道门确认，且澄清卡点已关闭；内容质量状态为 `content_approved`；若只完成授权草稿或内容仍为 `content_review_pending/content_revise`，必须停在 `design_draft`，不得把未确认草稿送入 Demo 制作。

## 6. 页面与视频的代表性闭环

按本轮路径执行适用部分。澄清门有效且完整设计已 `design_confirmed` 后进入 Demo 或正式媒体小样；非网页交付按工作范围矩阵执行其代表性闭环。

video_led_web网页设计必读[视频舞台](references/video-surface-contract.md)、[页面结构](references/page-structure.md)、[成品 UI](references/final-page-ui-quality.md)和[UI 证据](references/ui-quality-evidence.md)。先填写 `video_led_visual_gate`，再使用 UICraft 设计/实现；Web Design Guidelines 审查为必需；需要追加打磨时使用 Impeccable，不重复同一审查。

video_led_web网页实现时，写出时间线、事件、互动与返回契约后，再复制[视频页面模板](assets/video-led-course-page.template.html)及配套 CSS。使用动态背景或精确画面热区前，必读[呈现、背景与锚点契约](references/video-presentation-contract.md)，展开其数据模板，接入随包呈现模块并登记运行引用。模板是工作脚手架；用真实内容验证播放态视频主导、控件按需、暂停态单一工作面和窄屏阅读。

真实视频生产必读[视频生产系统](references/video-production-system.md)、[人物契约](references/character-reference-and-introduction.md)、[导演连续性](references/video-direction-and-continuity.md)、[声音连续性](references/voice-continuity.md)、[口语审阅](references/spoken-language-and-review.md)和[时间线质量](references/video-timeline-and-quality.md)。

先验证实际工具能力，建立实体参考与真实声音时序，再编译 shot 与 generation unit。新计划使用[视频计划模板](assets/video-production-plan.template.json)；参考来源记录与实际模型文件绑定分别核对。

选择最能暴露风险的完整链：包括本课适用的角色识别、首次介绍、声音、主要接缝、窄屏、互动、反馈和恢复。人物介绍须出现在实际视频内；合成人物图、网页姓名或字幕名不构成此项验收。

按第二道门确认最难媒体闭环。保留既有两道确认门，不增加逐人物、逐图片或逐镜头审批。

**本步完成**：本轮适用的页面或代表性闭环有实际产物和本版证据；正式小样完成适用人类确认。原型继续非视频实现，小样终点在此交付。

原生空间场景在教学与设计确认后读取[空间学习生产](references/spatial-learning-production.md)，按[场景计划](references/spatial-learning-contract.md)交接学科规则、结构/光色、操作反馈和状态恢复，调用threejs-anime-short的当前技术入口。核心镜头只是画质检查，Demo仍须完整知识动作和独立验收；未完成澄清/内容/设计门不得制作。hybrid_web的真实视频区间与空间桥接分别验收，不用一类通过替代另一类。

## 7. 全量生产与实现

读取[生产工作流](references/production-workflow.md)；执行媒体 Job 时读取[媒体任务运行](references/media-job-execution.md)，video_led_web实现时读取[实现落地](references/implementation-playbook.md)，原生空间/混合实现读取[场景契约](references/spatial-learning-contract.md)。在已授权范围继续组装、修复与验收；只有 `demo_accepted` 后才能进入正式成品生产，子工具静态结束不构成课程编排终点。

每次 Job 保留真实输入、指纹、attempt、终态、成本与输出关联；已提交任务续取，不重复提交。实体身份、物体数量、时序、发声、帮助和返回按[媒体互动连续性](references/media-interaction-continuity.md)复查。

新视频请求发送前执行媒体任务 owner 的最终参数读回与 `--pre-submit --unit` 关口；成片采用区间确定后执行时间线 owner 的源 PTS 接缝验收。计划、提交请求和实际输出分别核查，旧版未检查的新契约单列报告。

只有在交付终点已选择 `interaction_complete_prototype` 且交付终点门、`video_led_visual_gate` 全部通过时，原型才遵循工作范围中的 `video_only_delta`：完整课程内容、非视频资产、交互、反馈、修订、恢复与 UI 达到最终学生端水平；唯一可延期的是正式视频本体、真实时钟绑定与接入后回归。静态 HTML、占位画面或未实测页面必须保持 `design_draft/static_design_prototype` 标签。

必需媒体故障按契约重试或阻断；可选依赖按声明处理。已验收等价路线由操作者显式选择。内部生产解释留在工作记录；学习者只看到当前对象、动作、结果和自然接续。

**本步完成**：授权范围内所有必需产物组装完毕，Demo 已完成独立验收或明确停在 `demo_in_progress`；替代资产、未完成项和受影响的确认指纹准确记录。

## 8. 功能、试学与效果

按[工作范围](references/work-scope.md)的交付矩阵验收。视频网页执行真实播放、事件触发、正常/错误/帮助/修订、回看、刷新继续、桌面/手机、键盘/触摸、字幕与等价路径；记录本版浏览器操作和恢复证据。

人物和教学深度的语义质量需要实际审阅，校验器只检查可机械判断的字段、覆盖、文件身份与审阅记录。开放答案声明量规和判定责任；AI 评分仅在完成本课校准与批准后启用。

试学使用实际学习者记录版本、条件、表现、求助、修订与复查。效果评价报告样本、条件、缺失与不确定性，结果可为 supported、not_supported 或 inconclusive；未执行时写“未评估”。

评价任务、沉浸效果声明或相关媒体/交互变化，必须执行[沉浸评价](references/immersion-evaluation.md)的逐实例评审、适用的完整旅程与真实测量协议，并运行评审包校验。缺证据保持 null/未评；记录齐全不代表沉浸成立，实际学生感受与学习表现另报。

**本步完成**：达到授权 endpoint 的全部适用检查通过，未执行的人类确认、试学和效果评价准确标明。

## 状态与交付

正式七阶段、独立澄清/Demo 门禁与派生 `workflow_state` 以[流程状态](references/orchestration-and-status.md)为准。确认绑定实际文件与范围，经同一历史重放后生效；`browser_verified` 和小样存在不能替代 Demo 确认。

delivery endpoint、acceptance status 与 accepted scope 分别记录，不能替换上述状态。效果评价完成不等于效果获支持。

工作文件由范围矩阵派发，不固定文件数量。所有标识使用稳定英文全称。私有凭证、端点与设备标识留在本地配置；付费调用、外部写入与发布遵循用户实际授权。

课程包至少运行 `validate_course.py` 与 `validate_production.py --joint`。完整 Demo 另必须运行 `scripts/validate_content_quality.py <content-design-quality.json> --require-approved`、Demo 合同回归、知识动作覆盖、页面结构和浏览器实测；视频网页再运行参与、事件、视频生产、学习者文案和 `scripts/check_video_led_visual_gate.py <visual-gate.json>` 检查。动态背景或精确热区另按呈现契约执行结构与浏览器采集。命令细节读取对应 owner 或脚本 `--help`。任一适用检查失败，终点不得推进。追加清单事件保留上一不可修改快照并用 `--previous-manifest` 校验。

交付只报告实际文件与运行入口、当前状态、适配结果、已执行检查、未执行项和具体限制。Skill 维护则报告实际启用路径、通用改动与回归证据。

## 按需参考

以下只在分支触发时加载：

| 触发 | 按需参考 |
|---|---|
| 知识载体矩阵、完整 Demo 覆盖 | [知识载体与 Demo](references/knowledge-surface-and-demo-contract.md) |
| 内容候选发散、质量评分、Imagineering 体验增量 | [内容设计质量与 Imagineering 路由](references/content-design-quality.md) |
| 新课、重大教学改稿、教学分镜的首版生成或教法评审 | [学科教学与体验选择](references/subject-pedagogy.md)及其按知识类型路由的指南 |
| 沉浸构建、逐项评判、真实体验测量、全程或背景比较 | [沉浸设计取证与体验评价](references/immersion-evaluation.md) |
| 浏览器运行时、时钟与 seeking | [视频网页运行](references/video-led-web-course.md)、[实现落地](references/implementation-playbook.md) |
| 页面动态背景、逐帧热区、投影或遮挡 | [呈现、背景与锚点契约](references/video-presentation-contract.md) |
| 确定性 3D 或空间资产 | [3D 生产](references/three-dimensional-production.md) |
| 台词口语化、声音身份或替换 | [口语审阅](references/spoken-language-and-review.md)、[声音连续性](references/voice-continuity.md) |
| 实际媒体连续性失败 | [媒体互动连续性](references/media-interaction-continuity.md)、[导演连续性](references/video-direction-and-continuity.md) |
| 学习方法依据与适用边界 | [学习科学依据](references/learning-science-evidence.md) |
| 用户明确需要对应课型示例 | [试点示例](references/pilot-examples.md)，只作说明，不作为题材或媒体配额 |
| 专项聚合导航 | [戏剧与互动](references/drama-and-interaction.md)、[学习与媒体](references/learning-and-media.md)、[体验与资产](references/experience-and-asset-quality.md) |
