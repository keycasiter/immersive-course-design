---
name: immersive-course-design
description: Design, implement, validate, and evaluate immersive lessons. Use for course design or revision, student-facing Demos, course media, learner trials, and maintenance of this Skill. Route to the authorized endpoint and preserve actual confirmation and acceptance evidence.
---

# Immersive Course Design

从学习目标、知识动作和可观察证据推导教学，再推导世界、媒体和互动。先确定本轮能完成的阶段，完成一段实际工作并保存，再加载下一段材料。新课与重大改稿执行[大胆设计、小心求证](references/content-design-quality.md#大胆设计小心求证)：创作层作出鲜明选择，证据层集中核对，不让防御性声明淹没课程正文。

## 1. 派发

| 当前要求 | 先读的执行入口 | 本轮完成条件 |
|---|---|---|
| 优化本 Skill、路由、模板或校验器 | [Skill 维护](references/skill-maintenance.md)，同时使用 writing-for-agents | 授权维护实际更新启用目录并完成相关回归；仅审查保存问题和证据 |
| 单独生成/审阅教学分镜，或用多案例优化分镜 | [分镜独立审阅](references/storyboard-review.md)；维护同时进入 Skill 维护 | 实际分镜、范围与字节绑定、正文诊断及适用复测；不触发整课生产 |
| 参考外部课件、借鉴案例或扩充跨学科候选 | [外部课件参考库](references/external-courseware-reference-library.md)，再进入当前设计/分镜 owner | 标明实际观察层级、所用体验族、抽象结构与未验证范围 |
| 新课、重大改稿、设计稿、Demo | [执行与持续落盘](references/execution-flow.md) §1—2 | 先复用明确输入，完成可审设计，再按有效确认进入授权终点 |
| 评测既有设计、Demo、沉浸或验收主张 | [执行与持续落盘](references/execution-flow.md) §3 | 实际检查与版本证据、持续保存的报告、未执行项及可用结论 |
| 局部页面、媒体、台词或互动修改 | [工作范围](references/work-scope.md)，再读[执行与持续落盘](references/execution-flow.md) §1、4 | 修改覆盖授权范围，更新受影响的绑定、确认和检查 |
| 已确认设计的实现、媒体生产、启动或试学 | [执行与持续落盘](references/execution-flow.md) §4 | 从最早失效阶段恢复，达到已授权终点并保存真实证据 |

维护分支完成后退出课程流程。具体课程只作隔离验证样例，不写入通用规则。

## 2. 阶段门

新课与重大改稿先执行[澄清门](references/clarification-gate.md)。充分明确输入直接引用原证据；未决且会改变方案的决定才询问。设计草稿可继续完成，人类确认绑定实际版本。

- 设计稿终点是 `design_draft`；静态预览使用 `static_design_prototype` 标签。
- Demo 实现同时要求有效澄清、`content_approved` 与 `design_confirmed`。缺确认时先交完整可审设计和确认事项。
- 完整 Demo 按[工作范围](references/work-scope.md)与[Demo 契约](references/knowledge-surface-and-demo-contract.md)覆盖全课；唯一可延期工作由 `video_only_delta` 限定。
- 正式成品生产要求 `demo_accepted` 与适用最难媒体闭环确认。
- Agent 与脚本只记录真实授权、观察和执行结果；教师确认、审阅校准、真实学习者证据按各 owner 执行。

字段、状态及版本有效性按[归属表](references/contract-ownership.md)。终点、当前进度和验收状态分别报告。

## 3. 当前阶段读取

课程主链为：内容边界 → 候选发散 → 目标与证据 → 示范/引导/独立/修订/迁移 → 体验适配 → 媒体/页面 → 实现与验收。每段边做边保存；[执行入口](references/execution-flow.md)规定该段的最小读取顺序与落盘条件。

新建或修订独立评价／迁移任务时执行[评价完整性](references/course-evaluation.md#评价完整性合同)与实质迁移对照；科学观察与机制判断按[学科证据规则](references/subject-interaction-guidance.md#observable-evidence-in-science)核查实际可取得的材料。

完整阶段要求保留在 [COURSE-PIPELINE.md](COURSE-PIPELINE.md)。进入对应阶段时读取其相关节及 owner；字段缺口定点查 owner、模板或脚本 `--help`。实现或生产阶段的全文、模板与环境探测在其触发后加载。

`video_led_web` 必须使用[视频主舞台契约](references/video-surface-contract.md)：播放态视频主导，控制与章节按需显示；暂停态围绕同一视频事件只打开一个当前判断和主动作；反馈、关闭后回到原事件。生成页面前使用视频模板并完成 `video_led_visual_gate`，实际检查按阶段参考 §6—8 执行。

## 4. 完成与交付

课程设计达到[颗粒度标准](references/design-detail-standard.md)，全量内容有来源、教学、反馈、撤架和新材料独立任务。完整范围、教学质量、沉浸计划、版本绑定及全部适用结构检查保持原 owner 要求。

设计检查按阶段参考 §5 与[生产清单](references/production-manifest.md)执行；完整 Demo 和功能课程按阶段参考 §6—8 执行全部适用页面、媒体、浏览器与无障碍检查。结构 valid、页面可打开及自动化操作通过分别报告，不替代语义或真实学习效果。

交付链接指向实际文件或运行入口。写明授权终点、当前阶段、完成内容、实际检查、未执行项、确认事项和限制；首份工作快照不自动算完整交付。仍有已授权且可执行的工作，继续完成。
