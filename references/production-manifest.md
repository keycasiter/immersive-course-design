# 生产清单契约

`production-manifest.json` 是单课生产状态的唯一机器可读索引。课程设计、蓝图、媒体计划和验收报告仍保存具体内容；清单只引用它们并阻止状态、资产和治理信息失配。

复制 `assets/production-manifest.template.json`，用 `scripts/validate_production.py` 校验。

## 必填范围

`content_design.reference_identifier` 必须引用已注册 `content_design_quality` 文件；候选、审阅与严格准出的字段以 `content-design-quality.md` 1.1 为准。联合检查读取质量文件并核对 scoped blueprint 目标/来源，design 指纹包含质量及审阅实际字节。包版本变化而设计范围未变时，可沿既有 `bound_versions` 绑定仍有效的 design subject 版本，覆盖全部本轮目标；这不能保留已经改变的候选或审阅文件。

动态背景或精确锚点由 `demo_runtime/runtime_delivery.presentation_reference` 指向 `kind=video_presentation_contract`。其数据、实际主视频 SHA256 和资产依赖进入运行指纹，联合验收检查对应浏览器路径；字段与适配范围读取 `video-presentation-contract.md`。unused 时为 null，不凭空要求背景。

`work_scope.learner_delivery_type` 必须为 `interactive_web`、`facilitated_instruction`、`linear_media` 或 `print_or_document`，并按[工作范围矩阵](work-scope.md)派发代表性闭环与功能验收。`experience_profile` 只派发体验/页面模板；项目 profile 只提供可发现的语言、工具和环境默认。

`interactive_web` 沉浸式课堂的实现必须引用[视频主导课堂实现落地手册](implementation-playbook.md)，并在清单中登记运行时版本、视频事件图版本、入口文件、实际媒体哈希和浏览器验收证据。不能只登记页面截图或静态 DOM 作为运行交付。

- 课程标识、版本、当前状态与完整状态历史。
- 学习者画像：先修、语言、设备/场景、无障碍需要和未知项。
- 分层证据登记：`sourced_fact`、`reasoned_inference`、`teaching_scenario`、`unverified`。
- 设计与代表性闭环两道人类确认门、独立澄清/Demo 门禁，以及逐范围的版本、实际内容指纹和证据引用。
- 视觉圣经和最难代表性媒体闭环。
- 每项正式资产的教学作用、文件、来源、权利、隐私、披露、等价路径与验收。
- 评价能力和学习记录治理。
- 课程设计、蓝图、媒体计划、评价方案、核对记录和功能验收等证据文件。

## 交付终点与验收字段

清单顶层必须记录本轮交付终点和当前验收范围：

```json
{
  "delivery_endpoint": "design_draft|interaction_complete_prototype|media_sample|functional_course|learner_trial_ready",
  "acceptance_status": "not_started|structure_checked|browser_verified|media_verified|human_review_pending|accepted",
  "accepted_scope": "design|interaction|media|function|trial_ready",
  "acceptance_evidence": {
    "evidence_references": ["verification"],
    "review_owner": "实际审阅人或负责人",
    "accepted_at": "实际确认时间；未 accepted 时为 null",
    "reviewed_version": "实际被审阅的 course_version"
  }
}
```

`accepted_scope` 在 `acceptance_status=accepted` 时必填且必须精确匹配下表，其他状态为 `null`。它表示通过验收的层级，不替代 `delivery_endpoint`。

| `delivery_endpoint` | 允许的 `acceptance_status` | accepted 时的 scope | 最低 `current_status` |
|---|---|---|---|
| `design_draft` | `not_started`、`structure_checked`、`human_review_pending` | 不接受 `accepted` | `design_draft` |
| `interaction_complete_prototype` | `browser_verified`、`human_review_pending`、`accepted`；未完成时仍交付草稿 | `interaction` | `design_confirmed` |
| `media_sample` | `not_started`、`structure_checked`、`browser_verified`、`media_verified`、`human_review_pending`、`accepted` | `media` | `design_confirmed` |
| `functional_course` | `not_started`、`structure_checked`、`browser_verified`、`media_verified`、`human_review_pending`、`accepted` | `function` | `production_complete` |
| `learner_trial_ready` | `not_started`、`structure_checked`、`browser_verified`、`media_verified`、`human_review_pending`、`accepted` | `trial_ready` | `functional_accepted` |

最低状态只是字段组合的前置条件；标成通过还须具备该层全部适用证据。草稿的设计确认走正式设计门；原型的浏览器通过不签设计或媒体门。原型不使用 `media_verified`，功能课程不能借用 `trial_ready` scope，试学准备不能借用 `function` scope。

| 本轮产物 | 必需内容与证据 | 可留待后续 | 不能据此声明 |
|---|---|---|---|
| 设计草稿 | 决定、目标、蓝图、实际设计和未决风险 | 运行页面、正式媒体 | 学生端交付已完成 |
| 完整交互原型 | 完整课程内容、全部非视频资产、互动状态、反馈、恢复和 UI 证据；完整视频网页还须满足下方差额声明 | 正式视频本体、真实视频时钟绑定及接入后回归、真实试学 | 正式媒体、上线或学习效果 |
| 代表性媒体小样 | 本范围正式媒体与完整事件链、实际检查及适用确认 | 全量媒体与整课功能验收 | 整课功能通过 |
| 功能课程 | 本形态正式资源、运行、恢复、无障碍和适用功能验收 | 真实试学与效果评价 | 试学完成或学习效果 |
| 试学准备 | 可运行版本、任务、设备、适用同意/隐私条件、观察记录与反馈流程 | 真实试学结果 | 学习效果获支持 |

`acceptance_evidence.evidence_references` 必须引用 `evidence_files` 中真实存在的稳定标识；`reviewed_version` 必须等于当前被审阅的 `course_version`；`review_owner` 不能使用 Agent、脚本或生成器作为人类确认人。`accepted_at` 不能使用计划时间、占位时间或文件生成时间替代实际确认时间。

`delivery_endpoint` 与正式 `current_status` 分别记录。上表只定义交付产物的最低状态，状态转换、设计/代表性闭环确认和独立澄清/Demo 门禁以[流程状态](orchestration-and-status.md)为准；生成、浏览器通过或验收标签不自动推进正式状态。实际试学和效果评价继续使用正式状态与证据，不增加交付终点枚举。

注意：`work_scope.endpoint` 仍由[工作范围](work-scope.md)和生产校验器拥有，表示当前授权范围允许推进到的正式生命周期上限；顶层 `delivery_endpoint` 表示本轮实际交付的原型/媒体/课程产物。二者必须同时存在，但不能互相替代。`delivery_endpoint` 不得超过 `work_scope.endpoint` 允许的范围。

### 完整 Demo 的差额声明

当组合为 `full_course + interactive_web + video_led_web + interaction_complete_prototype` 时，必须提供：

```json
{
  "demo_completion": {
    "contract_version": "1.0",
    "completion_policy": "video_only_delta",
    "non_video_completion": {
      "course_content": "complete",
      "scene_and_beat_sequence": "complete",
      "page_and_responsive_layout": "complete",
      "interactions_and_feedback": "complete",
      "state_and_recovery": "complete",
      "accessibility_equivalents": "complete",
      "non_video_assets": "complete",
      "browser_verification": "complete"
    },
    "deferred_items": [
      {
        "deferred_identifier": "deferred_formal_video",
        "kind": "formal_video_generation",
        "asset_identifiers": ["video_introduction"],
        "reason": "正式视频本体尚未生成"
      }
    ],
    "video_replacement_contract": {
      "substitute_asset_identifiers": ["storyboard_introduction"],
      "formal_video_asset_identifiers": ["video_introduction"],
      "preserved_contracts": [
        "course_content", "layout", "interactions",
        "feedback", "state_and_recovery", "accessibility"
      ],
      "post_replacement_checks": [
        "media_timing", "hotspot_timing", "caption_sync",
        "return_state", "responsive_layout", "accessibility"
      ]
    }
  }
}
```

所有必需非视频正式资产和 `substitute_asset_identifiers` 必须已经 `accepted`。`deferred_items.kind` 只允许 `formal_video_generation`、`video_runtime_binding`、`post_video_integration_verification`，且只能引用正式 `linear_video` 资产。正式视频接入会触发媒体与功能回归，但不得重新定义课程内容、布局、互动判定或学习状态。

涉及页面设计或实现时，按[成品UI与布局](final-page-ui-quality.md)登记本版页面审阅和操作记录；逐资产审阅沿用原门禁。Demo 独立验收使用下方 checkpoint，截图不自动证明功能。

### 可执行编排与运行绑定 v1.0

新清单使用 `workflow_contract_version=1.0`，缺此字段不能按新流程准出。`workflow_state` 按[流程 owner](orchestration-and-status.md)从同一状态历史派生。

新增 `clarification_confirmation` 和 `demo_confirmation`，分别归属 `approval_subjects.kind=clarification/demo`。每种恰有一个全范围 checkpoint，其 `covered_identifiers` 必须等于工作范围的全部目标；确认沿用 `confirmation_identifier`、实际确认人、时间、范围版本、内容 SHA256、依赖指纹和 `human_confirmation` 证据。澄清 subject 的 bytes 材料包含 `clarification.intake_reference`；`clarification.confirmation_basis` 读取澄清 owner，两条合法值均须原用户证据，`unresolved_decision_identifiers` 必须为空。design scopes 依赖澄清，Demo 依赖澄清与全部设计 scopes。

Demo 使用 `demo_runtime`，正式视频使用独立 `runtime_delivery`；结构复制[运行绑定模板](../assets/runtime-delivery.template.json)。两个对象记录模式、course/runtime/event graph 版本、HTML 入口、JS/TS 源码、事件图、知识矩阵、浏览器执行和视觉门证据引用，以及 `bound_asset_identifiers`。文件证据分别使用 `runtime_entry`、`runtime_source`、`runtime_event_map`、`knowledge_surface_matrix`、`browser_execution`、`video_led_visual_gate` kind，并登记路径、当前版本和实际 SHA256。

入口/源码必须属于已验收 `runtime` 资产。Demo 的绑定覆盖全部必需非视频及分镜替代资产；正式运行绑定覆盖全部必需资产。浏览器记录和视觉门保存运行文件、矩阵、资产版本与实际文件的 `runtime_fingerprints`，更换任一绑定内容使旧证据失效。Demo 确认自动指纹包含 `demo_runtime`、差额契约、当前运行与资产字节、浏览器记录和视觉门；独立保留这些文件，正式视频接入不覆盖原 Demo 证据。

完整 Demo 和正式网页均读取矩阵/浏览器 JSON，校验逐目标、知识单元、Beat、运行定位、路径与视口覆盖。普通生产检查读取运行文件和目标路径，`--joint` 另与蓝图全量目标、知识单元、来源和必需 Beat 核对。浏览器 JSON 模板见[执行记录](../assets/browser-execution.template.json)，矩阵规则见[知识载体 owner](knowledge-surface-and-demo-contract.md)。明确 Agent/脚本自签被拒绝；身份真伪与教学语义仍由原审阅证据证明。

Demo `accepted` 还须 `acceptance_evidence.confirmation_identifier` 指向当前有效 Demo 确认，负责人等于实际确认人。确认记录者使用历史事件的 `recorded_by`，不能把它填成人类确认者。

非网页交付使用 `demo_delivery`，包含 `learner_delivery_type`、`content_reference` 与 `walkthrough_reference`，分别引用版本绑定的 `learner_materials` 与 `demo_walkthrough`。走读 JSON 保存 `course_version`、实际材料的 `material_sha256`、`checks`；逐目标覆盖 `normal/help_revision/return_reentry/accessible_equivalent`。检查行记录目标、path、passed 状态、实际结果/时间及 artifact 路径/SHA256。该分支不要求 HTML 或手机浏览器，但仍有独立 Demo 确认与当前材料指纹。

## 确认绑定

`course_version` 是交付总包版本；`approval_subjects[].subject_version` 是某个确认范围的内容版本。未改变的范围可以沿用原范围版本，不能以“总包版本变了”为由全部重确认，也不能仅凭范围版本没变而忽略实际文件差异。

每个 `approval_subjects` 条目使用稳定 `scope_identifier`，填写 `kind`、`subject_version`、实际 `scope`、`covered_identifiers`、`materials` 和 `editorial_changes`：

- `design`：归属设计门，必须覆盖 `learning_objectives`、`teaching_content`、`task_evaluation`、`remediation`、`independent_application` 五类内容。用 `components` 登记覆盖，用 `materials` 绑定实际目标、正文、判定、反馈/补救与新情境任务；列名齐全不证明内容正确。
- `media_contract`：归属媒体门。指纹自动包含清单的 `visual_bible`、`media_production_contract` 和其中 `voice_reference_identifiers`、`visual_reference_identifiers` 指向的实际文件。后者登记声线、口型、连续性和等价路径规则；有声音的已确认小样必须有实际声音参考。使用人物/环境等参考文件时必须列入视觉引用；没有参考文件时可留空并说明制作方法。媒体计划引用此约定，不维护另一份冲突规则。
- `media_sample`：归属第二道人类门。网页/视频 delivery 的指纹包含小样标识、交互路径、覆盖资产及实际文件；教师主持/纸面 delivery 可无媒体资产，但必须绑定代表性实施或完整材料走读证据。`materials` 另列运行入口、脚本、样式、主持材料、分支及未在资产表登记的依赖。

确认材料按真实依赖拆范围。想局部重确认，就先把实际内容拆成可独立绑定的文件或 JSON 子树；仍绑定一个全课正文文件时，该文件的教学改动影响整个绑定范围。新范围须确认，不能靠改名或删掉旧范围缩小已承诺的教学覆盖。

`materials` 支持：

| 字段 | 约定 |
|---|---|
| `source` | `evidence_file` 或 `manifest` |
| `reference_identifier` | 文件来源时引用 `evidence_files` 的稳定标识 |
| `fingerprint_mode` | `bytes` 对实际字节计算 SHA-256；`json` 对选定 JSON 内容规范化后计算 SHA-256 |
| `json_pointers` | `json` 模式必须显式列非空指针表；`""` 选择文件全文，其他值使用标准 JSON Pointer |

JSON 规范化只忽略缩进和对象键顺序，保留字符串、数值、数组顺序及其他内容。缺失指针报错；清单内指针只允许学习者、视觉、制作约定或评价能力的内容，不选确认自身或状态。指纹包含课程标识、范围标识、范围版本、覆盖描述和材料清单；不能悄悄换课程、版本或选定内容。

视频主导课的体验设计可选择 `/experience_profile/profile_identifier`、`/experience_profile/outline_reference`、`/experience_profile/beat_identifiers`、`/experience_profile/trace_matrix_reference`；不能选择整个 `/experience_profile` 或其 `coverage_status` 等审阅状态。新课/重大交互改稿将 `scene-interaction-plan.json` 登记为 `scene_interaction_plan` 文件证据并加入受影响设计范围的实际字节指纹。其他课型不采用参与计划时，移除模板中该文件证据及对应确认材料，不制造空计划。

先对实际待审材料运行：

```bash
python3 "<skill-root>/scripts/validate_production.py" \
  "<course-directory>/production-manifest.json" --show-approval-fingerprints
```

它只打印当前指纹，不写入确认。人类明确确认后，在对应门的 `confirmations` 中为每个范围保存：

```json
{
  "scope_identifier": "design_whole_course",
  "confirmed_by": "实际确认人",
  "confirmed_at": "实际确认时间",
  "confirmed_version": "实际确认的范围版本",
  "content_sha256": "实际待审材料计算出的64位小写SHA-256",
  "evidence_references": ["实际人类确认记录的证据标识"]
}
```

媒体门至少绑定制作约定与实际小样两个范围。进入相应已确认阶段时，所有归属该门的范围都须有当前有效确认。确认记录必须有稳定 `confirmation_identifier` 和 `dependency_fingerprints`（所依赖 scope_identifier → 实际确认内容 SHA-256）。确认追加至归档，经 reconfirm 事件成为当前绑定；未修改范围保留原记录与日期。Agent 不得代签或覆盖原指纹。

### 非语义修订

不改变教学含义的错字/排版不会使确认失效。JSON 缩进和键顺序变化直接得到同一指纹；其他此类修订须比对已确认材料与现稿，记录下面的 `editorial_changes` 条目，原确认指纹保持不变：

```json
{
  "classification": "non_semantic_editorial",
  "approved_sha256": "原确认的64位指纹",
  "current_sha256": "修订后实际内容的64位指纹",
  "recorded_by": "实际差异核对者",
  "recorded_at": "实际核对时间",
  "reason": "具体修改及教学含义不变的判断依据",
  "evidence_references": ["保存原稿、现稿差异和核对结论的证据标识"]
}
```

此记录必须精确匹配“原确认 → 当前稿”，多次修订后重新比对原确认与最新稿，不能使用模糊的永久豁免。只改非语义内容时保留范围版本；版本变化仍须重确认。数值、单位、条件、答案、否定词或画面/声音参考变化不能未经内容判断归入错字修正。判断不确定时按受影响范围重确认。

`media_sample` 禁用此豁免：实际已确认小样及其依赖变化必须重确认。同约定下重做其他素材仍按资产验收，未被小样绑定的资产文件不进入小样指纹。

### 校验边界

生产清单只接受当前结构；`workflow_contract_version` 标明本轮新增门禁，不提供自动迁移或推断旧确认。旧完整课缺新门禁时返回明确错误，不能复用旧 PASS 声称新流程准出。局部纯资产沿用自己的范围契约。

指纹校验发现受影响范围失配时阻断推进；原状态历史和确认凭据仍须保留。指纹是内容完整性检查，不是人的身份认证，也不判断两份文本在教学上是否等价。`--allow-missing-files` 不会豁免已确认范围的文件读取与指纹核对；模板放宽检查不作为正式准出。

## 证据分类

| 类型 | 使用方式 |
|---|---|
| `sourced_fact` | 可由教材、原始资料或已验证数据支持；必须给来源引用 |
| `reasoned_inference` | 基于事实作出的推断；必须写推理依据，不能冒充原文 |
| `teaching_scenario` | 为教学组织创作的人物、对白或事件；必须可识别为创作 |
| `unverified` | 尚未核实的工具能力、数据或内容；必须写核实动作，不能进入依赖它的正式结论 |

## 资产状态

`planned → draft → ready → accepted`。正式准出只使用 `accepted` 资产。生成成功、文件存在或编码可播放最多证明 `draft`/`ready`，不能自动成为 `accepted`。

每项资产都记录：

- `provenance`：来源类型、工具/模型、提示词或制作记录、输入资产。
- `governance`：权利依据、隐私审查、学习者披露和保存期限。
- `accessibility`：它服务的学习目标、等价路径及验收状态。
- `acceptance`：已执行检查与证据。

正式线性视频还须声明内嵌人声、环境/动作声、网页分轨和独立分支音频。静音 MP4 只能登记为中间资产。

每项使用固定 kind 枚举：linear_video、audio、panorama、three_dimensional、diagram、document、image、runtime；`delivery_class` 为 formal 或 intermediate。必需资源不能由 intermediate 满足。`formal_linear_video=false` 不构成声音豁免。

`asset_version` 和 acceptance.asset_version 必须一致；`acceptance.file_snapshots` 按 files 同序保存每个 path、content_sha256。实际解码、内容、连续性、等价路径分别进入 checks 和证据。正式视频还要求 voice_content、lip_synchronization、timbre_continuity、mix、实际 ffprobe 证据；校验器探测真实音轨，听审仍需人执行。separate_branch_audio 可以为 not_applicable，但须写 branch_audio_not_applicable_reason；网页分轨仍必须保留。

小样的 media_modes、candidate_asset_versions、risk_coverage 与实际已 accepted 候选资产绑定；模式须与实际覆盖资产类型一致。风险行含 risk_identifier、critical、selection_reason、status、evidence_references。content、continuity、mobile、equivalent_path、return_and_recovery 为共同关键风险，必须实测passed；声音/口型、投影、模型规则按实际模式加入关键风险。其他不适用项填 not_applicable_reason；关键项planned阻断媒体门，占位资源不能代表正式质量。

## 评价与数据

- 封闭或确定任务可用规则评价。
- 开放答案默认采用学习者自评量规或人工审阅。
- AI 评价仅在已有代表性样例验证时启用，记录适用范围、不确定性和失败回退；未经验证不得标成自动掌握判断。
- 学习记录默认本地最小化保存。若上传或关联身份，必须填写界面披露、目的、保存期限、导出和删除路径。

verified_ai 与 enabled 必须一致。AI 配置还填 evaluator_identifier、evaluator_version、prompt_version、rubric_version、objective_identifiers、configuration_evidence_references；validation_binding 绑定这些已验证值，并用 configuration_fingerprints 绑定实际评价器/提示词/量规文件。任何绑定改变使验证失效；回退为实际 self_review 或 human_review，不产出自动掌握结果。

## 追加事件与当前状态

范围按[工作范围](work-scope.md)声明。approval_subjects 增加 depends_on_scope_identifiers，使用真实依赖且禁止循环；默认小样依赖设计与制作约定，制作约定可独立于未改变的教学范围。依赖集合一经进入历史即不可原地修改；依赖变化创建新的 versioned scope 并显式迁移，旧 invalidate 始终按旧 scope 的依赖语义回放。

`inherited_confirmations` 使用结构化记录，并解析 `parent_manifest_reference` 核对父确认 ID、scope、subject version、内容 SHA256、active 状态和父清单 SHA256。只有字段存在而无法解析父清单时只能作为草稿，不得准出。

status_history 每项包含 event_identifier、event_type、status、recorded_at、recorded_by、reason、course_version、scope_identifiers、evidence_references、evidence_fingerprints、previous_event_sha256、event_sha256。首项前哈希为 null；事件哈希是排除 event_sha256 后的规范JSON SHA256。确认后推进事件必须保存每个实际证据文件当时的SHA256；改写同一引用的哈希不能沿用原阶段结果。

- advance：从 design_draft 开始逐级推进；不得重复或跳级。相应门必须已有有效确认，阶段结果有实际证据。
- reconfirm：confirmation_identifiers 引用归档中的确认；scope_identifiers 与这些确认完全相同。只更新范围绑定，status保持当前阶段；初次确认亦使用此事件。
- invalidate：列受影响范围和原因，依据依赖传播撤销小样及后续结果。设计失效退回 design_draft，媒体失效退回 design_confirmed；保留所有原事件、确认和证据。

同约定下的非小样资产重做，只撤销实际受影响的后续阶段：invalidate填写 affected_asset_identifiers 与 invalidated_from_status（production_complete及以后），范围列表可为空，状态退回该阶段的前一阶段，设计与小样确认保留。已确认小样文件或教学/制作约定变化仍必须失效对应scope，不能用资产失效豁免。

production_complete及以后每个advance保存asset_snapshots（正式accepted资产标识→asset_version、完整file_snapshots）。旧阶段绑定与当前交付文件不一致时阻断；受影响生产、浏览器、试学或效果检查重新执行后追加新advance，不能只刷新旧快照。

current_status 与 approval_gates.status 必须符合事件重放结果。旧有效确认仍核对实际文件指纹；已失效归档只留历史，不要求当前稿匹配旧指纹。改稿后不能保持过期阶段等待脚本自动“修正”。

每次追加先保存上一份清单。使用 --previous-manifest 对比完整历史前缀、确认归档和范围保留；仅当前文件的哈希链不能发现整体截断/重建。`--show-event-fingerprints` 只输出计算值，不自动改历史或代签。

## 联合一致性与证据

--joint 读取 evidence_files 中唯一 course_blueprint，核对标识/版本、所选目标、必需资源及kind、正式文件、来源引用、评价阶段、任务继续条件和完全一致的学习记录字段。标成 completed 的评价必须与课程实际阶段一致；设计评审可以在 design_draft 完成，不自动等同人工确认。

正式阶段证据登记 path、kind、course_version、content_sha256、bound_identifiers；评价证据涵盖本范围目标。总包版本变化而原范围不变时，用 bound_versions 保存 scope_identifier/asset_identifier → 原版本，实际文件和事件指纹必须仍一致；未变证据可继续有效。新教学范围或资产版本不能借用旧证据。非语义修订的依赖保留原确认指纹，不因现稿排版哈希变化要求重确认。

effect_result 用 conclusion=supported / not_supported / inconclusive，另写 objective_identifiers、conditions、uncertainty、retention_and_transfer_scope、evidence_references。effect_evaluated只声明过程完成。

## 校验

```bash
python3 "<skill-root>/scripts/validate_production.py" \
  "<course-directory>/production-manifest.json" --joint \
  --previous-manifest "<previous-manifest-snapshot>"
```

校验器检查结构、阶段证据及确认范围的版本/内容绑定，不判断教学内容、媒体观感、权利法律结论或学习效果。任何相关人工结论都必须有实际证据引用。
