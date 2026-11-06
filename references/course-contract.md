# 课程蓝图契约

蓝图用于检查目标、节点、任务与媒体的连接，可作为不同播放器的内容输入。它不绑定官网 IDL、PSM、账号服务或特定模型。运行框架可以增加字段，但应保留这些关系。

## 顶层

| 字段 | 内容 |
|---|---|
| `schema_version` | 新模板为 `1.2`；`1.1`保留原完整设计校验，`1.0`仅支持基础读取 |
| `course_identifier` | 稳定英文标识 |
| `course_title` | 课程标题 |
| `course_version` | 内容版本 |
| `learning_core` | 教学核心：学完能自己完成什么 |
| `opening` | 所有课程必填的背景引入、问题与主线入口衔接 |
| `sources` | 来源标识、标题、位置、版本或日期、核实状态 |
| `learning_objectives` | 标识、可观察目标、是否必需、来源标识 |
| `media_resources` | 标识、类型、教学作用、必需性、制作状态、实际文件与投影 |
| `scenes` | 课堂节点 |
| `entry_scene_identifier` | 主线入口 |
| `summary_scene_identifier` | 结果与回顾节点 |
| `completion_policy` | 完成与理解结果的文字规则 |
| `evaluation_plan` | 目标证据、任务映射、评价阶段与记录 |
| `knowledge_organization` | 1.2知识单元、关系、基础诊断、顺序理由及整合任务 |
| `instructional_design` | 1.2逐目标教学对齐；可声明教学循环扩展，登记整任务、示范、引导练习、独立应用与表达反思 |

标识使用小写英文、数字、单个连字符或下划线，不混入具体部署位置。

## 知识组织与教学对齐（1.2）

1.2保留全部1.1字段和检查，另外要求以下对象。新课与重大教学改稿采用1.2；已确认1.1课程可以继续按原契约使用，不因 Skill 更新自动迁移或重做。需使用新学习设计检查时，在新设计版本补全字段并审阅。

`knowledge_organization`：

- `prior_knowledge_check`：实际基础诊断、未知项与支持方式的非空说明。
- `units`：非空列表。每项有稳定 `knowledge_identifier`、非空 `description`、有效且非空的 `source_identifiers` 和 `objective_identifiers`、布尔 `assumed_known`，及 `teaching_scene_identifiers`。
- 本课教授的单元关联必需 `macro`／`instruction` 场景；已知基础可有空教学列表，但仍需诊断说明。每场可使用目标子集，所列场景合起来覆盖单元目标；同一知识跨目标复用时保留共同标识，只有内容真正不同时拆分。
- `relations`：列表，可为空。每项有 `from_knowledge_identifier`、`to_knowledge_identifier`、`relation_type` 及非空 `rationale`。关系类型为 `prerequisite`、`part_of`、`causal`、`contrast` 或 `representation`；方向分别表示 A 是 B 的先修、部分、原因、对比对象或对应表征。对称关系只写一次即可。
- 单元不得自连；仅先修关系必须无环，机制反馈环不受这一限制。
- `sequence_rationale`：知识依赖、教学顺序、叙事时间与整合的说明。单元只有一个或没有关系时解释理由，不为过校验编造关系。
- `integration_task_identifiers`：非空，可关联一个或多个必需核心练习／取证任务或独立任务，合起来覆盖必需目标。它检查引用和声明覆盖，不证明任务要求了足够知识整合。

`instructional_design.objective_plans` 对每个必需目标有且只有一项：

- `objective_identifier`。
- 非空 `knowledge_identifiers`，单元应关联此目标。
- 非空 `teaching_scene_identifiers`，关联覆盖此目标的必需 `macro`／`instruction`。
- 非空 `guidance_and_fading`、`retrieval_and_spacing`、`transfer_change`，说明实际指导与撤除条件、可实施的检索／间隔范围及迁移变化。短课无课后触达时可说明范围与理由，不把“不适用”伪装成已执行。

知识依赖与实际教学顺序是否合理由内容评审判定；脚本不要求按节点排列顺序讲课，也不为理论框架设配额。

## 教学循环扩展（instructional_design.contract_version 1.0）

该局部契约不改变蓝图 `schema_version`。新课与重大教学改稿声明扩展并运行 `--instructional-cycle`；历史1.2蓝图未声明时保留原学习设计检查，不自动迁移。

`instructional_design.whole_task` 必填：

- `description`：贯穿本课的完整问题、判断、解释、作品或操作，不必是大型项目。
- `presentation_scene_identifier`：学习者首次看见完整任务或最终表现的必需场景；该场景须位于所列引导练习和独立任务之前的所有路径上。
- `learner_output` 与 `success_standard`：最终提交及成立标准。
- `sequencing_strategy`：`demonstration_first`、`attempt_first` 或 `mixed`。
- `sequencing_rationale`：依据先修、复杂度、试错代价和首次尝试的诊断价值说明选择；字段合法不证明顺序合理。

每个必需目标的 `objective_plans` 在原字段外增加：

- `demonstration`：`decision` 为 `included` 或 `not_required`，始终写 `rationale`。included 需给非空 `scene_identifiers` 与 `content`，关联覆盖目标的必需教学场景，并写实际过程、理由、适用条件和自检；not_required 不列场景，不能只写“简单”。
- `guided_practice_task_identifiers`：非空，引用覆盖目标的必需 practice 任务。
- `independent_task_identifiers`：非空，引用覆盖目标的必需 transfer / independent_assessment 任务。
- `application_conditions`：区分引导练习可用的答案性帮助、独立应用保留的正常资料与工具、操作帮助和无障碍支持。
- `articulation_and_reflection`：`decision` 为 `dedicated`、`embedded` 或 `not_required`，始终写 `rationale`。前两者给非空 `task_identifiers` 与实际 `prompt`；not_required 不列任务。反思不自动算掌握，脚本只查任务覆盖，不判断提示是否真正要求依据、条件或比较。

扩展不要求所有课程采用相同顺序，不新增固定章节、场景种类或审批门。示范可为例题、思维外显、对比例、作品修订或操作演示；探究型课程可以先尝试，但不能要求学习者猜对未教内容。结构校验不判断示范准确性、帮助是否真的撤除、独立任务是否泄露答案或反思质量。

`--instructional-cycle` 要求蓝图1.2并隐含完整学习设计检查。声明 `contract_version` 或 `whole_task` 时会自动检查整个扩展，不能通过删减单项字段规避。

## 开场与目标成功标准（1.1）

`opening.scene_identifier` 必须指向 `entry_scene_identifier`，入口为必需节点。引入可与首场融合，不必新增独立序章，但必须填写：

- `background_input`：必要背景及实际画面、对白或旁白。
- `prior_knowledge_connection`：已有认识连接、基础不足时的等价输入。
- `motivating_problem`：由事件或疑问引出当前问题。
- `learner_role`、`first_action`：学习者关系与可理解的首个教学动作。
- `transition`：背景与首场的对象、视线、动线、声音或概念衔接。
- `understanding_check`：如何检查开场理解，不强制答题，不自动算核心知识掌握。

每个目标添加非空文本列表 `success_criteria` 与 `anticipated_difficulties`，分别声明成功标准和预期误解、技能或解释困难。填写字段不能代替人工检查目标与任务是否相符。

## 开篇呈现扩展（opening.contract_version 1.0 / 1.1 / 1.2）

这些版本属于 `opening` 局部契约，不改变蓝图 `schema_version`。`1.0` 检查课程定位、背景、任务前呈现和恢复；`1.1` 在此基础上增加情境进入与世界转换声明；`1.2` 再增加面向零背景学习者的开篇启动包。新课与重大沉浸入口改稿采用 `1.2` 并运行 `--opening-design`。历史 `1.0/1.1` 保持兼容，不因 Skill 更新自动迁移或失效；未声明扩展的历史1.1/1.2蓝图保留原检查。声明任一扩展字段时自动检查整个扩展，不能删除版本字段来逃过检查。

保留原七项开篇说明，新增：

| 字段 | 契约 |
|---|---|
| `contract_version` | 字符串 `1.0`、`1.1` 或 `1.2`；新课使用 `1.2` |
| `course_introduction` | 面向学习者的实际主题、学习用途及能力介绍，不只写标题 |
| `entry_mode` | `standalone`、`embedded` 或 `resumed`；独立小样和不可验证上文的深链接采用 standalone |
| `first_task_identifiers` | 非空、无重复；各入口分支最先遇到的学科任务，不能遗漏或用后续任务替代 |
| `information_units` | 非空信息单元列表；数量按实际内容决定，一段可有多种用途 |
| `essential_terms` | 列表，可为空；必要名称/符号/指标逐项写 `term`、`meaning`、有效 `information_identifier`；语义准确性另审 |
| `reentry_policy` | 实际版本核对、缺记录回退、本地背景回顾和答案保留规则 |
| `experience_entry` | `1.1/1.2` 必填的情境进入对象；`1.0` 不要求 |
| `orientation_bootstrap` | `1.2` 必填的零背景覆盖对象；`1.0/1.1` 不要求。只保存假定入口状态、各信息目的的覆盖角色和引用，不复制 `information_units` 正文；人物、系统、对象、画面和动作可共同承担，不固定欢迎、简报或转换顺序 |

`orientation_bootstrap` 写学习者首次进入时实际获得的启动输入，不把课程标题、目标表、NPC称号或“开始任务”当作背景。若存在 NPC/主持者，`host_welcome` 和其关联的 `scene.narration` 必须形成可录制、可字幕化的场景任务简报：地点欢迎、场景用途、身份关系、正常状态、当前事件、任务目标、参与步骤、最终产出、支持边界和第一动作。可以由多段对白和现场动作共同完成，但不能只在设计说明里概括：

| 字段 | 契约 |
|---|---|
| `assumed_entry_state` | 明确默认不了解的世界、对象、角色、术语和流程，以及可验证继承的先修 |
| `host_welcome` | NPC、主持者、旁白或界面怎样实际问候、表明身份、指向对象并建立可回应关系；无人物时写等价主持 |
| `minimal_world_model` | 用新手可理解的语言说明系统/时代/场景通常做什么、为何重要、当前对象处于哪里 |
| `key_objects_and_terms` | 首动作前必须认识的对象、名称、符号和状态怎样随实物、画面或短演示建立含义 |
| `learning_journey_preview` | 接下来会观察、尝试、修订和最终产出什么；不是章节目录、制作节点或答案路线 |
| `role_and_collaboration` | 学习者、NPC/系统和其他角色分别负责提供材料、判断、操作或回应中的哪一部分 |
| `first_action_handoff` | 哪句实际台词和哪个对象动作把启动说明交到第一项有效行动 |
| `comprehension_safeguard` | 不要求预先知道什么；不理解时怎样用样例、重述、词义、静态图或朗读补齐 |

`experience_entry` 写实际设计状态，不写“营造氛围”或“播放视频”：

| 字段 | 契约 |
|---|---|
| `intensity` | `compact`、`standard` 或 `extended` |
| `reality_anchor` | 学习者可理解的现实地点、物件、消息、问题或日常操作 |
| `inciting_event` | 与核心问题有因果关系的变化、异常、委托或发现 |
| `threshold_transition` | 前后状态、连续线索及空间/时间/声场/视角/界面的可感知变化 |
| `identity_landing` | 人物、工具、权限、工作位置或对象移交怎样确认学习者能做什么 |
| `first_consequential_action` | 无需未教学科结论即可完成、且会改变现场状态的动作 |
| `persistent_carrier` | 贯穿教学、练习、反馈与结课并保存痕迹的物件、记录或模型 |
| `world_rule_continuity` | 开场建立的目标、限制、对象和反馈怎样继续约束后续任务 |
| `accessibility_equivalent` | 静音、低动态和媒体失败时怎样落到同一背景、身份与状态 |
| `skip_replay_reentry` | 跳过动态、重看和恢复怎样保留对象、记录、首答和下一动作 |
| `design_rationale` | 所选强度及进入结构与学习目标、内容复杂度和制作条件的关系 |

首任务按图遍历到的 `core_reasoning`、`evidence_collection` 或 `independent_assessment` 判定，进入它即停止该分支；`orientation`、`operation_support` 不算学科任务。声明角色是否合理由内容评审判断，不能改标签来绕过背景。先修诊断若要求学科判断，也纳入首任务。

每个信息单元填写：

- 稳定、唯一 `information_identifier`；非空 `purposes`。1.0/1.1 至少覆盖 `course_introduction`、`background`、`problem`、`learner_role`、`first_action`；1.2 还须覆盖 `host_welcome`、`world_model`、`journey_preview`。不是要求八个独立段落，同一段可承担多种用途。
- 有效 `scene_identifier`。该场景可从入口到达，并位于每个首任务之前的所有路径上；同场呈现允许。不能把背景放在后续补救或可跳过的支路。
- `delivery` 为 `inline` 或 `inherited`。
- `content_reference` 仅取明确的正文入口：`opening.course_introduction`、本单元场景的 `scene.narration`，或本单元的 `inherited_context.content`。引用必须解析成非空正文；承担课程定位的单元必须包含声明的 `course_introduction` 正文，不能只挂用途标签。
- 非空 `presentation_reference`，定位本版实际脚本、镜头、字幕或页面及事件；规划时写可制作的位置，实现后由页面契约绑定实际组件。同一段内的揭示顺序按实际脚本/事件审阅。
- `presentation_event`：inline 只能为 `scene_enter` 或 `before_task_open`；inherited 只能为 `verified_prior_context`。
- `media_resource_identifiers` 是有效资源列表，可为空；有媒体时同时关联所声明场景。纯文字不强制制作媒体。
- 非空 `equivalent_content` 与 `equivalent_presentation_reference`，给出本地静音/媒体失败背景正文及首任务前呈现入口；文本存在不证明播放器已经显示。
- inline 的 `inherited_context` 为 `null` 或缺省。inherited 必须有对象，包含非空 `course_identifier`、`course_version`、`presentation_reference`、`content`、`replay_reference`，对应父内容版本、先前实际呈现位置与正文及回顾入口；仅 embedded/resumed 可继承。

继承条件运行时逐次核对实际呈现记录和当前版本。无法核对、上文未呈现或版本不符时，先在本单元场景展示本地等价正文，再开放任务。父文档、确认或回顾链接存在不能单独证明看过。脚本检查声明与本地回退信息，不认证学习者历史或父内容的可用性。

`--opening-design` 隐含完整设计检查且要求蓝图1.1/1.2；与 `--learning-design` 同用时要求1.2。原 `--learning-design` 不对无扩展的旧1.2稿新增要求；新流程同时使用两个开关。联合清单校验会自动检查已声明的开篇扩展。

结构检查、内容评审、实际呈现和真实理解分别成立。脚本不识别术语语义、不检查自由文本位置是否对应运行UI、不评判信息充分性或学习效果；按[开场引入](course-opening.md)完成正文审阅、浏览器验收和实际试学，未执行项单列。沿用现有两道确认门，不新增审批或必答入门题。

`1.2` 的结构通过只证明零背景启动字段、情境进入字段和任务前呈现用途完整。NPC 是否自然且匹配场景、最小世界模型是否足够、路径预告是否清楚且不泄露答案，以及现实锚点是否可信、阈限是否自然、身份是否带来行动权限、第一动作是否真的改变现场、持续载体是否贯穿，分别由内容审阅、浏览器验收和真实试学确认。`1.1` 只证明原情境进入字段非空且强度值合法，不自动获得零背景启动准出。

## 来源与资源

来源状态为 `provided` 或 `verified`。提供了材料不等于已核对版本与正确性；核实结论仍需记录在设计稿。

资源类型：

- `video`：推进或局部观察。
- `panorama`：宏观叙事；填写实际 `projection`。
- `three_dimensional`：局部模型。
- `diagram`：精确图形、流程或数据教具。
- `audio`：旁白与环境声。
- `document`：证据与资料。

教学作用用 `progression`、`macro_narrative`、`local_exploration`、`explanation`、`evidence` 或 `support`。视频不必只承担推进，但承担推进的资源应为视频；宏观全景采用 `panorama` 与 `macro_narrative`。

资源制作状态为 `planned` 或 `ready`。`file_path` 在未制作时为 `null`；实际制作后可以填写相对蓝图文件的路径或文件 URL。标为 `ready` 时填写真实本地文件，不把规划路径写成可用资源。远程资源可在设计中记录来源，验收交付时保存经过验证的本地文件。

图片有正确投影声明，仍需进行视觉验收。资源状态不代表教研或浏览器验收已通过。

## 节点

| 字段 | 内容 |
|---|---|
| `scene_identifier` | 稳定标识 |
| `title` | 节点标题 |
| `kind` | `introduction`、`macro`、`instruction`、`practice`、`transfer` 或 `summary` |
| `required` | 是否在主线必须经过 |
| `objective_identifiers` | 对应目标 |
| `media_resource_identifiers` | 关联资源 |
| `narration` | 实际课堂事件、旁白或讲解 |
| `task` | 无任务为 `null`，有任务填写任务对象 |
| `next_scene_identifier` | 无任务节点的下一节点；任务节点用结果路径，结果节点为 `null` |

基础说明、拓展和分支可作为额外节点，不要求固定数量。`macro` 节点关联宏观全景；模型讲解与操作使用 `instruction` 或 `practice`。

## 任务

任务包含稳定标识、题干、响应形式、结果与解释依据、反馈、补救和路径：

- `task_identifier`、`prompt`、`response_type`。
- `evaluation.expected_result` 与 `evaluation.explanation`。开放题写评价要点，允许多种合理回答。
- `feedback.success` 与 `feedback.needs_help`。
- `recovery.hints`、`recovery.explanation`、`recovery.retry_available`。
- `outcomes.success`、`outcomes.needs_help`，必要时增加 `outcomes.continue_after_review`。

响应形式使用 `choice`、`numeric`、`ordering`、`variables`、`pathway`、`evidence`、`constructed_response` 或 `performance`。这是任务分类，不代表自动评分已实现。

1.1及1.2任务另填：

- `pedagogical_role`：`core_reasoning`、`evidence_collection`、`orientation`、`operation_support` 或 `independent_assessment`。
- `cognitive_action`：学生自己完成的思考或明确辅助动作。
- `learning_evidence`：答案、依据、关系或作品；辅助任务声明只记录引导/操作，不计掌握。
- `removal_cost`：删掉或简化的损失，据此评审价值与注意力成本。

1.1及1.2的必需目标教学覆盖来自 `macro` 或 `instruction`，不能只靠开场挂目标；练习覆盖来自 `practice` 中的核心推理或取证任务，独立检查来自 `transfer` 中的 `independent_assessment`。取证是否要求足够思考仍需内容评审，不能用点击收集代替理解。

`needs_help` 通常返回当前节点或对应补救节点。新情境任务可通过 `continue_after_review` 进入回顾，让尚未独立完成的学生仍能结束学习过程；结果记录为仍需练习。不得把这条路径当作答对。

原子任务 success 必须推进，不允许指回自身；多步骤用不同 scene_identifier 表达子状态与进展。校验同时检查连续正确路径可达结课，不能依赖答错或求助才离开。continue_after_review 的默认前置条件是已保存尝试且已查看反馈；新模板显式填写 outcome_conditions.continue_after_review=["attempt_saved","feedback_viewed"]，联合校验要求该声明。

## 作答、评价、帮助与表现

四种状态分别保存，不由提交、勾选自评或查看反馈推断掌握：

| 记录字段 | 可用值与含义 |
|---|---|
| submission_status | not_attempted / draft / submitted；提交后保留首次原答与版本 |
| evaluation_status | not_evaluated / pending_review / met / partially_met / not_met / unassessable |
| assistance_status | independent / operation_help / knowledge_help；分别保存实际帮助，知识提示影响独立证据 |
| objective_performance | not_demonstrated / needs_practice / demonstrated_with_help / independently_demonstrated |
| evaluation_source | deterministic / self_review / human_review / verified_ai；附评价器或量规版本 |

pending_review 不记零分或掌握；partially_met 展示已成立部分和待修订要点；unassessable 说明缺证据或表达/操作障碍并提供补取证。self_review显示“学习者自评”，保留其声明与依据，不自动写 independently_demonstrated。只在允许的评价来源、条件和证据满足独立成功规则时记录独立表现。

所用状态由任务类型选择，不强迫每题拥有全部状态。待审可以继续课程，但需已保存尝试且已查看对应说明/反馈；结课页展示实际来源与待审状态。运行验收记录这些状态转换和首次答案保护。

## 贯穿评价（1.1）

`evaluation_plan.objective_evaluations` 对每个必需目标包含：

- `objective_identifier`、`evidence`、`independent_success_rule`。
- `practice_task_identifiers`：非空，关联该目标的必需练习中核心推理或取证任务。
- `independent_task_identifiers`：非空，关联该目标必需迁移节点中的独立评价任务。

`design_review`、`learner_trial` 和 `learning_effectiveness` 各有 `status`、`method` 与 `evidence_references`。状态为 `planned`、`not_evaluated` 或 `completed`；已执行必须关联非空证据说明，未评估说明当前范围或后续方法。声明已执行不等于证据质量通过。

`record_fields` 至少包含 `material_version`、`first_response`、`assistance_used`、`operation_help`、`knowledge_help`、`feedback_revision` 和 `independent_result`。材料版本、首次、帮助、修订与独立表现分别记录；参与指标不得代替学习证据。

## 形成性闭环与评价条件（1.2）

`evaluation_plan.objective_evaluations` 另填非空 `rubric_reference` 与 `assessment_conditions`，给出量规实际位置及材料、工具、帮助、提交与反馈条件。脚本只查文本，量规内容、链接及合理性仍按设计稿审阅。

`evaluation_plan.formative_assessment` 是非空检查点列表，覆盖每个必需 `practice` 中的核心推理／取证任务，不把领路、翻页或独立测量阶段当成练习诊断：

- 每项 `task_identifier` 唯一且指向对应练习。
- `evidence_interpretations` 非空，每项写 `objective_identifier`、`observed_response`、`interpretation`、`alternative_explanation`、`instructional_action` 和 `recheck_task_identifier`。
- 目标属于当前任务；再查是覆盖该目标的必需核心练习／取证任务或独立任务，可引用当前任务的实际修订，也可引用后续新任务。不得在保存独立首答前执行泄露答案的反馈。
- 同一任务的主要困难按需要增加解释条目，不强制数量；证据无法解释时写补取证或待审动作，不伪造自动诊断。

1.2记录字段再包含 `evidence_interpretation`、`instructional_action` 与 `recheck_result`。按目标保留必要判断和动作，不要求上传或保存无限原始交互日志。

## 校验方式

```bash
python3 "<skill-root>/scripts/validate_course.py" "<course-directory>/course-blueprint.json"
python3 "<skill-root>/scripts/validate_course.py" "<course-directory>/course-blueprint.json" --complete-design
python3 "<skill-root>/scripts/validate_course.py" "<course-directory>/course-blueprint.json" --learning-design
python3 "<skill-root>/scripts/validate_course.py" "<course-directory>/course-blueprint.json" --learning-design --opening-design
python3 "<skill-root>/scripts/validate_course.py" "<course-directory>/course-blueprint.json" --complete-design --ready-media
```

默认按声明版本检查结构，允许模板待填项；1.0仅支持基础检查。`--complete-design` 要求1.1或1.2字段、有效任务映射且替换所有待填项。`--learning-design` 隐含完整设计检查并要求1.2；`--ready-media` 还要求必需媒体存在且标为可用，关联必需目标的来源已核实。

校验内容包括：标识与引用有效、目标有来源和成功标准、入口有开场引入、任务有教学作用/证据/评价/补救、评价映射成立、必需目标有教学／练习／迁移检查、节点可从入口到达且可到结课、主线不能绕过必需节点。
1.2再检查知识与教学目标覆盖、先修环、整合任务声明覆盖、形成性检查点及再查目标一致。开篇扩展检查正文与媒体引用、入口分支首任务及不可绕过的前置呈现场景；声明时序不等于实际呈现。结构成立不代表关系、解释或评价科学合理。

通过结构检查不等于内容正确或课程已可学习。还需要原课审校、实际媒体、播放器行为与试学记录。
