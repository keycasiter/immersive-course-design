# 互动载体实现矩阵

本文件把互动载体映射到实现技术、适用学科和可观察学习证据。它是技术选型参考，不把学科和媒介强绑定；最终选择仍由知识动作、对象、设备和验收条件决定。

## 1. 选择顺序

按以下顺序选型：

```text
学习者必须完成的知识动作
→ 当前视频事件中的对象或关系
→ 最小可用互动载体
→ 确定性反馈和状态
→ 设备、无障碍和恢复成本
→ 是否需要升级技术复杂度
```

优先使用能够支持同一学习证据的最简单技术：

```text
HTML controls / DOM
→ SVG / Canvas 2D
→ Web Audio / Media APIs
→ Three.js
→ WebGL / WebGPU / 外部服务
```

3D、实时协作、后端或 AI 评分不能因为“更沉浸”就自动获得优先级。

## 2. 载体与技术矩阵

| 互动载体 | 默认技术 | 典型知识动作 | 更适合的学科/内容 | 不适合的情况 |
|---|---|---|---|---|
| `scene_control` 直接控件 | HTML button、checkbox、radio、range、select、Pointer Events | 指认、选择、配对、少量调节、两状态比较 | 历史证据选择、语言选择、基础科学变量、数学参数观察、地理定位 | 需要长文阅读、复杂空间或连续结构操作 |
| `scene_card` 场景卡 | DOM、语义 HTML、`dialog`、`aria-live` | 当前判断、短问题、提示、反馈 | 所有学科的局部判断和即时反馈 | 背景介绍、长资料、多题问卷、永久任务中心 |
| `document_reading` 文档阅读 | HTML、CSS columns、分页/锚点、文本选择、标注层 | 原文取证、引用、比较、批注 | 历史、语文、法律、社会科学、文学、语言 | 只需一句事实或只需观察动态过程 |
| `object_inspection` 对象查看 | DOM、SVG、Canvas 2D、图片热点、放大镜 | 局部观察、部件识别、结构对照 | 生物图、艺术作品、工程图、地图、实验器材 | 需要真实空间遮挡或连续物理运动 |
| `deterministic_tool` 确定性工具 | TypeScript reducer、SVG/Canvas、数学/规则函数 | 计算、测量、标注、验证规则 | 数学、物理、化学、编程、数据分析、语言结构 | 结果依赖不可验证的生成模型 |
| `guided_experiment` 引导实验 | DOM 控件 + deterministic model + Canvas/SVG | 预测、操作变量、观察结果、解释差异 | 物理、化学、生物、地理、经济和系统科学 | 没有明确变量、规则或可观察结果 |
| `simulation` 仿真 | TypeScript 规则模型、状态机、Canvas 2D、Web Worker | 预测、运行、比较、敏感性分析 | 科学实验、生态、气候、经济、历史决策约束、工程系统 | 只有装饰变化，或无法说明模型假设 |
| `spatial_360` 全景 | `<canvas>`、WebGL panorama viewer、equirectangular texture、Pointer Events | 环视、定位、观察空间关系 | 地理、建筑、博物馆、考古、自然科学、职业安全 | 二维图已经能提供同等证据，或移动端无法定位 |
| `spatial_3d` 三维视图 | Three.js、GLB/GLTF、OrbitControls、Raycaster | 旋转、剖切、部件关系、空间操作 | 解剖、生物、工程、建筑、地理、物理空间 | 只是为了展示模型，没有结构判断任务 |
| `timeline_replay` 时间轴回放 | `<video>`、Media APIs、事件注册表、Canvas/SVG overlay | 回看、预测、比较前后状态 | 历史、实验过程、语言发音、操作流程、自然现象 | 互动与视频事件没有时间关系 |
| `evidence_linking` 证据连线 | SVG paths、DOM drag/pointer events、确定性 graph model | 证据与主张连接、关系判断 | 历史、法律、语文、社会科学、数据分析 | 只有点击连线，没有证据适用性判断 |
| `assembly_practice` 部件组装 | DOM drag/drop、Pointer Events、SVG/Canvas snap rules | 结构组装、步骤顺序、部件关系 | 工程、机械、生物结构、化学装置、职业培训 | 组装结果不对应规则或教学对象 |
| `virtual_instrument` 虚拟仪器 | DOM controls、Canvas、Web Audio、deterministic model | 读数、调参、操作顺序、故障定位 | 物理、化学、生物、音乐、工程、职业技能 | 仪器行为无法由规则解释 |
| `dialogue_practice` 角色对话 | DOM state machine、固定选项、可选语音输入 | 选择回应、语用判断、解释立场 | 语言、历史、社会科学、医学沟通、职业培训 | 由生成模型自由推进剧情且无法验收 |
| `speech_input` 口语输入 | MediaRecorder、Web Speech API 或已授权语音服务、人工复核 | 发音、口语表达、解释 | 语言学习、演讲、口语沟通、音乐基础 | 需要高风险自动评分但没有校准集 |
| `sound_recognition` 声音辨识 | HTMLAudioElement、Web Audio API、波形/频谱可视化、标签选择 | 区分音色、节奏、环境声和信号 | 音乐、语言、物理、自然科学、职业安全 | 自动分类模型没有可解释反馈 |
| `annotation_creation` 批注/创作 | `contenteditable`、Canvas/SVG、文本编辑、草稿状态 | 标注、解释、构图、写作、作品修改 | 语文、历史、艺术、设计、科学记录 | 作品标准不明确或无法提供反馈 |

## 3. 技术落地规则

### 3.1 直接控件和场景卡

适合使用原生 HTML：

```html
<button data-action="select-evidence" data-option-id="evidence-01">
  选择证据
</button>
<input type="range" min="0" max="2" step="1" data-variable="pressure">
```

状态由 `CourseRuntime` reducer 更新，按钮只派发事件。不要用视觉变化代替反馈；每次操作必须能说明当前状态、规则结果和返回行为。

### 3.2 文档、证据和批注

使用语义 HTML 保存完整材料：

- `<article>` 或 `<section>` 保存原文；
- `<mark>` 或 SVG overlay 保存选区；
- 锚点保存原文位置；
- `contenteditable` 保存草稿；
- `localStorage` 保存短期恢复；
- 评价要求长期证据时再显式接入后端。

不能把长文拆成大量卡片来制造“互动感”，也不能提前高亮正确证据。

### 3.3 图表、地图和关系图

优先使用 SVG：

- 文本和标签由代码渲染；
- 线、节点、区域可访问；
- 支持键盘焦点和触摸；
- 通过稳定 `data-object-id` 与事件图绑定。

Canvas 只在对象数量、绘制频率或画笔能力使 SVG 不适合时使用；Canvas 需要额外提供键盘/文本替代层。

### 3.4 确定性工具和仿真

仿真必须拆成三层：

```text
输入 schema
→ 可复现规则函数
→ 结果与解释
```

示例：

```ts
type SimulationInput = {
  variableA: 0 | 1 | 2
  variableB: 0 | 1 | 2
}

type SimulationResult = {
  state: string
  visibleChanges: string[]
  explanation: string
}
```

相同输入和课程版本必须得到相同结果。模型假设、适用范围和不确定性必须在互动中可见。

### 3.5 全景和三维

只有在学习目标需要空间关系时才使用：

1. 先做二维图或局部控件；
2. 证明二维不能提供同等证据；
3. 再引入全景或三维；
4. 为手机、键盘、字幕和无障碍提供替代路径；
5. 记录实际使用的生成源码/规则、GLB或全景图、纹理、相机和命中区域版本。

Three.js可直接生成正式教具，也可加载DCC资产；按[空间学习生产](spatial-learning-production.md)分开验收学科规则、几何/光色/动画和实际操作，不把工具路径当画质证明。二维/三维选择可在设计依据充分时直接作出，不要求无目的先做一个二维试片。

### 3.6 语音和声音互动

- 语音录入必须保存权限状态、音频格式、时长和失败原因；
- 自动结果只能做提示或候选判断；
- 高风险或高影响判断必须允许人工复核；
- 声音辨识必须显示可解释的听觉特征或对照；
- 声音事件由当前主媒体的时钟和事件注册表控制；原生空间路线不伪造视频时间线。

## 4. 学科选择建议

这不是固定映射，而是初始匹配：

| 学科/内容类型 | 首选载体 | 可升级载体 |
|---|---|---|
| 历史/社会科学 | 时间轴、文档阅读、证据连线、角色约束卡、地图 | 关系网、局部谈判仿真、场景对话 |
| 语文/文学 | 原文阅读、批注、角色对话、作品创作 | 语音表达、声音辨识、场景化改写 |
| 外语 | 对话、口语输入、声音辨识、字幕对照 | 角色分支、语音反馈、情境仿真 |
| 数学 | 直接控件、SVG 图形、确定性工具、参数仿真 | Canvas 几何、动态函数、空间模型 |
| 物理/化学 | 虚拟仪器、引导实验、变量仿真、结构组装 | 3D 装置、空间测量、Web Audio |
| 生物/医学 | 对象查看、标注、结构拆解、流程演练 | 3D 解剖、虚拟仪器、病例决策 |
| 地理/地学 | 地图、时间轴、全景、数据图表 | 3D 地形、空间测量、环境仿真 |
| 工程/职业技能 | 步骤演练、虚拟仪器、部件组装、故障定位 | 3D 设备、空间安全演练、语音沟通 |
| 艺术/设计 | 作品查看、批注、构图、创作和对照 | 3D 空间、声音/节奏、材质操作 |

## 5. 载体准入判断

每个互动在 `scene-interaction-plan.json` 中说明：

```text
knowledge_action
carrier
why_this_carrier
simpler_alternative_considered
input
feedback
evidence
recovery
accessibility_equivalent
```

以下情况不得进入正式实现：

- 选择载体的理由只有“更沉浸”“更高级”或“更好看”；
- 直接点击、旋转或拖动就是全部学习动作；
- 互动没有可见后果；
- 反馈依赖不可复现的模型输出；
- 3D/全景没有二维和无障碍替代路径；
- 载体无法从当前视频事件进入或返回；
- 实现复杂度明显超过学习证据的需要。
