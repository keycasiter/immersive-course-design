---
name: immersive-course-design
description: 用于设计、改编、制作或打磨以 Three.js 实时场景承载的沉浸式课程，以及维护本 Skill。覆盖观察、探索、视点、对话和对象操作；普通动画短片由 threejs-anime-short 负责。
---

# 沉浸式课程设计与制作

把值得理解的内容转成可以亲历的情境：学习者进入现场，注意具体对象，观察或参与变化，从现场回应中发现关系。Three.js 承载实时主场景；网页层承载可读资料、公式、对话和必要控件。

## 先定位任务与当前阶段

核对用户已有材料、项目入口、已确认决定、目标设备和当前问题。沿用真实授权与已完成产物，从最早缺失环节接续。只询问会改变内容含义、参与方式、范围或成本的未知决定；可从项目核实的先自行核实。

| 请求 | 从哪里开始 | 当前交付边界 |
|---|---|---|
| 新课、文字/材料改编 | 下方主链路第 1 步 | 完整可感知设计；授权制作时继续 |
| 代表场景、完整课程 | 读取[生产流程](references/production-workflow.md)，核对现有设计与确认 | 候选成品场景或全课及相应证据 |
| 改人物、声音、场景、页面或运行问题 | 定位受影响内容，再读[人物声音](references/character-and-sound.md)、[空间制作](references/spatial-production.md)、[页面](references/page-and-accessibility.md)或[运行](references/runtime-contract.md) | 修复、相应复验和变更影响；保持有效确认 |
| 审阅设计、验收作品、观察学习者 | 设计读[体验设计](references/experience-design.md)；成品读[验收](references/validation.md)；真实走访读[体验观察](references/experience-review.md) | 有证据的判断、问题与未覆盖范围 |
| 维护 Skill、模板或工具 | [维护](references/skill-maintenance.md)与[同步约定](AGENTS.md) | 方法与工具；不自动启动课程制作 |

## 制作主链路

**内容依据 → 完整体验设计 → 设计确认 → 代表成品场景 → 代表场景确认 → 全量制作 → 真实验收与交付**

操作细节、命令与阶段产物只在[生产流程](references/production-workflow.md)维护。以下是执行地图；到达对应阶段再读取其参考。

| 步骤 | 要完成的工作 | 进入下一步的判据 |
|---|---|---|
| 1. 内容变成经历 | 读[内容与语境](references/content-and-context.md)、[体验设计](references/experience-design.md)。核对来源与范围，写实际入口、画面、台词/资料、参与、回应和结束 | 每项必需内容都能定位到具体感知或事件；陌生读者能复原完整经历 |
| 2. 设计交接到实现 | 制作时读[场景契约](references/scene-contract.md)、[运行契约](references/runtime-contract.md)。把语义、表现约定和真实实现入口分别落实到计划，编译可读主稿 | 设计确认对应实际内容；对象/规则/事件/操作有稳定 ID 和可实现接口 |
| 3. 做成代表场景 | 读[空间制作](references/spatial-production.md)，涉及人物/有声时读[人物声音](references/character-and-sound.md)。选择最能暴露全课风险的一段，以候选最终品质做完整闭环 | 进入—观察/参与—可见变化/回应—继续/返回真实可用；品质与设备证据齐，代表场景获确认 |
| 4. 扩展全课 | 复用已确认的结构、风格、接口与规则，逐场完成并复验；页面读[页面与等价参与](references/page-and-accessibility.md) | 所有必需内容、场景、互动与接续可达，逐场问题闭环 |
| 5. 验收并交付 | 读[真实验收](references/validation.md)，按[生产与版本](references/production-and-version.md)绑定当前文件与证据 | 当前构建的内容、画面、动作、操作、声音及恢复得到实际验证；报告入口、覆盖、缺口 |

设计和代表场景是两处集中人工检查；复用已有明确授权。先完成可审材料再请求缺失决定，不额外设置全课 Demo 或逐对象审批。确认字段与失效范围由[生产与版本](references/production-and-version.md)定义。

## 贯穿全程的约定

### 内容与体验

- 每个主要对象、视点和动作都服务一个具体关系或处境。安静观察也可承担内容；角色按需要出现，首次进入交代地点、对象和首动作背景。
- 学习者通过世界的自然回应继续体验；本路线不编排测验、评分或答对解锁。探索可退出、返回与重看，可选热区不要求全点。
- 来源事实、解释、创作和模型近似分别说明。数学/科学关系由可靠规则求值，几何、数值和标签共享结果；实际学习效果需真实学习者证据。

### 制作与品质

- 默认以代码生成 Three.js 主场景；GLB、Blender、预渲染影片不作前提。视点、画风与设备预算由本课内容决定。
- 代表场景属于成品，使用候选最终品质。先让主形、连接、尺度、信息主次和动作成立，再处理材料、光色与细节；用目标视口的实际画面判断。
- 通用 Three.js 技术优先协同已安装的 `threejs-anime-short`，先读其 SKILL 再按问题补读。本 Skill 拥有教学语境和交接；依赖不可用时按[空间制作](references/spatial-production.md)处理。
- 场景计划拥有生产期语义，运行状态拥有当前经历，生产清单拥有真实确认与验收。[归属表](references/contract-ownership.md)定义唯一写入处。局部改动复验影响面，合并与交付核对全量；连续两次同类修正失败时重查表示或前置设计。

## 需要时再读

| 触发条件 | 参考 |
|---|---|
| 不会把设计填进计划，或接到状态与代码 | [完整实施示例](references/worked-example.md)；示例是方法，不是新课题材模板 |
| 人物动机、分镜、换视点或前后接续不清 | [情境与分镜](references/situation-and-storyboard.md) |
| 使用资料、图像、声音、字体或生成服务 | [来源与资产](references/sources-and-assets.md)、[项目偏好](references/project-production-profile.md) |
| 借鉴优秀作品或研究某种制作方法 | [参考研究](references/reference-research.md)；研究范围不自动启动制作 |

当前合同为 2.0；旧课程保留原合同，不自动迁移。普通制作无需阅读维护与历史说明。
