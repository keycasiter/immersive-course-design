# OpenMontage 方法采纳索引

研究日期 2026-11-05。来源是 [OpenMontage](https://github.com/calesthio/OpenMontage/tree/d21f5d4eaa08422b09c7091757a05affcbabb35b) 的固定提交 `d21f5d4eaa08422b09c7091757a05affcbabb35b`。全树盘点后核读有关编排、输入审阅、缓存、确定性节奏与恢复的源码和测试；没有声称全文读完全部工具与 Skill。精选文件 SHA、阅读范围与公开定位见 `assets/openmontage-adoption-sources-20261105.json`。

按 writing-for-agents 把方法放进单一 owner，主入口只派发；模板和机械检查接通，语义仍须实际观察。代码独立实现，未复制其 AGPL-3.0 源码或安装它的运行时。源码与同仓测试属于一个项目来源，不是多个独立研究来源；项目宣传不作为生产或学习效果证据。

| 借鉴点 | 原项目证据 | 本 Skill 的归属与落地 |
|---|---|---|
| 规划前审阅实际媒体、抽帧逐源隔离 | source_media_review helper、schema、real_media tests | [输入实检](source-media-admission.md)，来源清单/实检模板，source 分支 SHA、解码与实际抽样身份检查 |
| 输入内容与输出格式进入复用身份、dry-run 不动资产 | base_tool、asset_cache、缓存格式与 dry-run tests | [媒体任务](media-job-execution.md)，原 Job/attempt 与当前请求/台词、实际输出完整性、保留已有文件；视频采用新路径已接入原 delivery 检查 |
| 从可控渲染器计算事件时间，对齐实际声音 | verify_scene_pacing、screen-demo pipeline | [时间线](video-timeline-and-quality.md)，精确事件/对象对应、渲染与音源版本、trace 及成片/浏览器实测分列 |
| 当前阶段加载、部分进度恢复与分支身份 | AGENT_GUIDE、checkpoint、resume_identity tests | [制作流程](production-workflow.md)，按依赖恢复并复用现有状态/版本，主入口不展开全部专项 |
| 可选进度 observer 与正确性记录分离 | events、provider_jobs | [制作流程](production-workflow.md)，统计展示可降级，必需记录仍是推进依据 |

## 修正后采纳

- source_media_review 在探测前设置 reviewed=true，schema 又不强制探测和内容观察；空列表可同时表示无输入与无法审阅。本 Skill 分开 not_supplied 与失败，并重读实际文件，不把标签当通过证据。
- asset_cache 恢复检查 blob 是否存在，未复核输出内容 SHA，且可能先删除目的文件。本 Skill 复核实际源/目的字节，异内容保留；损坏或缺失优先恢复原任务，不自动回退付费生成。
- verify_scene_pacing 按最近时间匹配任意 landmark，没有比对 cue 的事件含义。本 Skill 要求同事件/对象的对齐与实际看听；trace 检查不声称语义验收。
- seed 不证明提供方确定性。当前只实现已选视频资产的机械复用检查，未建立自动随机生成缓存引擎。

## 未采纳

70% motion 的切镜计数、MP4 后缀即可算动态、固定方案/来源/增强密度、统一预算、强制 BGM、逐 stage 额外审批、同时展示两个 runtime 都未成为课程规则。正式媒体按每个必需教学区间验收，来源、推断与生成分别登记。

本轮回归使用独立合成媒体与记录，只证明检查和合法恢复路径有效。未执行 OpenMontage 全量生产、付费模型调用、真实课程制作或学习者效果试验；这些不在 Skill 维护任务的完成声明内。
