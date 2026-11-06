# 执行与持续落盘

本文件拥有 Agent 的阶段读取、首份工作快照、接续、委派和命令取证规则。它不改变内容、颗粒度、范围、确认、Demo 或沉浸验收标准；各 schema 与准出条件仍由[归属表](contract-ownership.md)派发。

## 1. 确定当前能做的工作

读取用户输入与当前实际文件，记录请求终点、当前阶段、授权范围和最早缺失/失效项。新课先读[澄清门](clarification-gate.md)；已有有效决定复用原证据，充分输入按该 owner 继续。

用户要 Demo 而没有已确认设计时，当前动作是完成可供确认的设计。页面模板、浏览器环境与正式生产脚本在进入实现阶段后加载；先完成确认所需的实际材料。

每阶段维护 `verification.md`：当前完成内容、下一项动作、实际检查与缺口。恢复任务先读该文件和实际产物；记录陈述与文件冲突时，以当前字节和原始执行证据核对。

**完成条件**：本轮请求与当前可执行阶段明确；不能推进的门有实际理由，仍可执行的设计/审查工作已列出。

## 2. 新课与设计草稿：三次落盘

### 第一次：实际课程主稿

首轮只读用户来源、[澄清门](clarification-gate.md)和[内容设计质量](content-design-quality.md)。据已知输入创建 `clarification-intake.md` 与 `course-design.md`，再进入后续参考。

主稿写实际内容边界、核心目标的候选与取舍、独立表现、示范/引导/独立教学链、持续事务及必需节点的首版材料、台词、动作和反馈。事实与情境创作分开；缺项集中列入核验区，不在每个场景重复风险和未执行声明。按[大胆设计、小心求证](content-design-quality.md#大胆设计小心求证)先完成鲜明、具体的课堂，再把版本状态、确认和证据限制集中写入 `verification.md`。已知资料、题干或反馈直接写正文，不能只有章节名和待办清单。

候选发散在世界、剧情与媒体规格之前完成。`content_review_pending` 等状态如实保留；自拟分数用于比较候选，不冒充教师审批。

**完成条件**：上述两份文件实际存在且含本课可阅读内容；首稿是可继续补全的工作快照，状态在文件头或核验区标记一次，不用防御性声明反复打断正文。

### 第二次：按缺项补成完整设计

读取[颗粒度标准](design-detail-standard.md)，以其模块和所有必需节点形成缺项表。逐模块读对应 owner，立即填回产物。已满足且无矛盾的模块复用；一项的定点查阅完成后，先落盘再换模块。

| 正在补的模块 | 对应读取 |
|---|---|
| 来源、目标覆盖、知识关系与教学链 | 阶段参考 §2—3；`work-scope.md`、`knowledge-organization.md`、`instructional-design.md`、`knowledge-to-immersive-experience.md`、`subject-interaction-guidance.md` 的适用学科 |
| 体验候选、Imagineering 增量、PBL 适配 | 阶段参考 §3；`imagineering-for-learning.md`、`pbl-fit-screening.md`；其他组合只在实际选择后读取 |
| 开场与持续事务 | 阶段参考 §4；`situated-entry-and-world-transition.md`、`course-opening.md`、`narrative-scale-and-perspective.md`、`experience-framing-and-learner-language.md` |
| 逐 Beat 分镜、对白、资料、分支、反馈和恢复 | 阶段参考 §4；`narrative-storyboard-integration.md`、`storyboard-review.md`、`experience-blueprint.md`、`storyboard-and-interaction-spec.md`、`beat-production-specification.md`、`spoken-language-and-review.md`；人物出现时读人物契约 |
| 知识载体、输入与界面状态 | `scene-participation-design.md`、`interaction-surface-implementation-matrix.md`、`course-contract.md`、`interaction-and-atmosphere.md`、`knowledge-surface-and-demo-contract.md`；视频网页设计同时读 `video-surface-contract.md` |
| 评价与沉浸计划 | `course-evaluation.md`、`immersion-evaluation.md`；构念与原子定义按 immersion owner 引用；草稿创建计划，不填未发生的观察 |

“阶段参考”指 [COURSE-PIPELINE.md](../COURSE-PIPELINE.md)。所有触发的规则仍必须执行；按当前模块读取，不要求先汇总整个参考树。对模板先查所填字段，按校验错误定点补查；只在维护验证器或定位其具体错误时读源码。

**完成条件**：颗粒度标准的全部适用模块、所有必需节点与分支均有实际材料；配套分镜、蓝图、互动规格、沉浸计划和评价计划已保存，标识一致，验证表能定位到正文。

### 第三次：机器编译、实际检查与确认交付

此时读取阶段参考 §5、[生产清单](production-manifest.md)与[流程状态](orchestration-and-status.md)，使用适用 JSON 模板编译真实设计。确认记录留待实际负责人；事实来源临时或未获教师审阅时保持内容待审。

运行阶段参考与 owner 要求的适用检查。完整范围、开场、教学链和完整设计选项按本轮范围启用；草稿内容质量检查不使用 `--require-approved` 冒充已批准。命令结果按 §5 保存。失败先记录实际错误，再修订对应字段或内容并重跑；失败、未运行、接口调用错误分别列出。

新建或修订独立评价／迁移任务时，按 `course-evaluation.md` 生成并运行 `assessment-integrity.json` 合同检查，同时按 `instructional-design.md` 审阅实际基线、新材料和推理变化；科学观察任务按 `subject-interaction-guidance.md` 核查证据可取得性。局部修订同样执行适用检查，不等待整课生产包。进入 Demo 后实际验证整组反馈与恢复入口，静态通过不抵运行验收。

**完成条件**：达到完整设计颗粒度，实际检查及未满足项均可复核；草稿终点与内容/设计确认状态准确。请求 Demo 但缺确认时，交这些材料并指出确认者、审阅对象、版本与继续条件，不创建越门页面。

## 3. 既有交付与验收主张审查

仅审教学分镜时先走 [分镜独立审阅](storyboard-review.md)，保存局部正文与范围记录后交付；未被请求的整课 JSON、Demo、媒体和学习者验收不在该路线加载。审查完整交付或验收主张时继续以下步骤。

1. 读取要求、实际入口、清单与被主张的证据，立即创建 `evaluation-report.md`。先保存核对对象、版本、检查范围和未执行项；后续每个观察更新报告。
2. 优先核对当前文件 SHA256 与运行/确认绑定，并运行对应入口检查。先用 `--help` 查真实接口。命令调用失败只证明本次没有取得该项结果。
3. 静态核对、结构校验、实际浏览器、媒体实检、沉浸审阅、真实学习者结果分别取证。只审验收主张时不制作课程；实际体验审查提前执行最有判别力的浏览器/媒体路径，随后扩展到 owner 要求的完整矩阵。
4. 每取得一项证据，就保存观察、文件/位置、结果和它能支持的结论。超时或能力不可用时保留已完成报告，标记未执行范围，继续其他独立检查。
5. 沉浸任务读取 `immersion-evaluation.md`：记录契约 valid、覆盖、校准、实际观察和真实学习者结果分别核对。人类签字不补足缺失观察或校准；没有证据的原子保持 null/未评。

**完成条件**：实际检查范围可定位，结论仅覆盖已观察证据，正式验收仍执行全部适用 owner 门；报告不会只剩“接下来检查”的计划。

## 4. 已确认阶段与有限委派

已有有效设计按阶段参考 §6—8 进入本轮实现、生产或试学；局部修改按工作范围保持父状态，更新受影响的确认和证据。输入媒体触发准入实检，付费/外部写入按实际授权。

若使用子 Agent，为其指定一个明确模块、输入、输出文件或带原文位置的发现、适用 owner、停止条件。父 Agent 同时完成独立模块；接回后核实来源和标识并保存。参考摘要只作辅助，不是课程交付。充分输入且没有并行制作/核对需要时，由父 Agent 直接推进产物。

**完成条件**：委派返回能直接填入或修订实际交付；不存在“所有子 Agent 完成全规范摘要后才开始写”的依赖。

## 5. 命令证据

使用 owner 的实际 CLI 和 `--help`，保持校验器本身的退出码。可以直接捕获 subprocess 的返回值、stdout、stderr，或使用随包 `scripts/run_check.py --record <结果.json> -- <命令及参数>`。

运行器保存真实 argv、cwd、起止时间、返回码及完整输出附件，返回子命令状态。查看输出前几行应在命令结束后读取附件；流水线末尾工具的 0、通用 shell 的 0 或 JSON 中的 valid 不替代各项验收判据。每次结果使用独立文件名，保留失败后再跑的历史。

**完成条件**：报告引用原始结果，能区分命令成功、记录有效、覆盖完整与验收成立。工作中断也能从真实产物、缺项和最后结果接续。
