# 视频主导沉浸式课堂实现落地手册

本文件是 `interactive_web + video_led_web` 的规范实现方法。它规定实现边界、目录、运行时职责、数据契约和交付证据；它不是可以直接交付的页面模板。默认技术方案是 **Vite + TypeScript + 原生 HTML/CSS + 原生 HTMLVideoElement**。React 只用于确实需要复杂组件树时，Three.js 只用于确实需要空间结构或 3D 操作时；它们都不能替代本文件规定的运行时职责。

## 1. 实现目标

交付的是一个能在普通浏览器中运行的沉浸式交互课堂：

```text
HTMLVideoElement
  → VideoClock
  → EventRegistry
  → InteractionAdapter
  → LocalFeedback / LocalState
  → ResumeSnapshot
  → 回到同一视频事件
```

视频时间线是课程推进的唯一权威。互动层是事件内的局部体验，不是另一个课程系统。学习者的操作可以改变当前视图、临时对象状态、仿真参数、阅读位置或即时回应；默认不改变课程主线，不创建长期分支，也不要求持久证据。

## 1.1 默认技术栈

除非项目已有明确技术约束，按以下方式实现：

| 能力 | 默认实现 | 允许替换的条件 |
|---|---|---|
| 构建 | Vite 5+、TypeScript 5+、npm | 项目已有稳定构建系统且能输出同等静态资源 |
| 页面 | 原生 HTML 语义元素、CSS、少量 TypeScript DOM 控制 | 复杂组件树才引入 React；不能因为使用 React 就新增第二套状态机 |
| 视频 | 原生 `HTMLVideoElement`、`requestVideoFrameCallback` + `timeupdate` fallback | 不能用播放器组件接管课程进度；播放器库只能提供外观或兼容能力 |
| 状态 | 小型 reducer + 单一 `CourseState` store | 不引入 Redux 等全局状态库，除非已有应用统一使用且仍保持单一 store |
| 互动 | `InteractionAdapter` 接口和事件注册表 | 复杂互动可独立模块化，但必须通过适配器进入/退出 |
| 3D | Three.js，仅用于已批准的空间目标 | 2D、DOM、Canvas 或视频已足够时不得引入 |
| 本地恢复 | `localStorage` 保存小型快照；IndexedDB 保存较大草稿或离线资源 | 不默认连接后端；需要账号、上传或长期证据时另行声明 |
| 单元测试 | Vitest 或项目既有等价工具 | 必须覆盖 reducer、事件匹配、跳转阻断和恢复 |
| 浏览器验收 | Playwright | 必须覆盖真实 `<video>`、事件暂停、互动返回和错误路径 |

标准启动和验收脚本：

```json
{
  "scripts": {
    "dev": "vite",
    "build": "tsc --noEmit && vite build",
    "preview": "vite preview",
    "test": "vitest run",
    "test:e2e": "playwright test",
    "validate:runtime": "python scripts/validate_video_led_runtime.py app/data/video-event-map.json app/index.html app/runtime/course-runtime.ts"
  }
}
```

`validate:runtime` 做事件图、页面结构和运行时契约的静态检查；`test:e2e` 必须在 `npm run build` 后针对实际构建产物运行，不能只验证 `.ts` 源码而不验证浏览器实际加载的 JavaScript。

`playwright.config.ts` 的 `webServer` 必须启动构建预览而不是开发服务器：

```ts
webServer: {
  command: "npm run preview -- --host 127.0.0.1",
  url: "http://127.0.0.1:4173",
  reuseExistingServer: !process.env.CI
}
```

标准验收顺序是：

```bash
npm run build
npm run validate:runtime
npm run test:e2e
```

## 2. 规范实现目录

正式网页实现必须能映射到下列责任，不要求文件名完全相同，但不得把所有职责塞进一个 HTML 或一个组件：

```text
course-package/
├── package.json
├── tsconfig.json
├── vite.config.ts
├── playwright.config.ts
├── course-manifest.json
├── design-outline.md
├── verification.md
├── app/
│   ├── index.html
│   ├── data/
│   │   ├── video-event-map.json
│   │   ├── scene-interaction-plan.json
│   │   └── content-registry.json
│   ├── runtime/
│   │   ├── course-runtime.ts       # 组装运行时，不拥有第二套时间线
│   │   ├── video-clock.ts          # 读取 video.currentTime
│   │   ├── event-registry.ts       # 事件匹配与完成条件
│   │   ├── interaction-adapters.ts # 直接控件/阅读/仿真/空间视图
│   │   ├── state-store.ts          # 当前局部状态和恢复快照
│   │   └── recovery-controller.ts  # 错误、重试、关闭、回看、刷新
│   ├── components/                 # 场景内可复用视图
│   ├── interactions/               # 具体互动逻辑和局部反馈
│   ├── styles/
│   │   ├── tokens.css
│   │   ├── scene.css
│   │   └── responsive.css
│   └── assets/
│       ├── video/
│       ├── captions/
│       ├── audio/
│       └── interaction/
└── tests/
    ├── contract/                   # JSON / Beat / ID 契约
    ├── runtime/                    # reducer / event / restore
    └── browser/                    # Playwright 正常与异常路径
```

静态原型可以减少 `components/`、`tests/` 和正式媒体，但必须在 `verification.md` 标记为 `design_draft` 或 `prototype`，不能声称已经具备视频运行时。

## 3. 运行时职责

### `video-clock`

唯一允许读取课程推进时间的模块。它只订阅：

- `loadedmetadata`
- `timeupdate`
- `seeking`
- `pause`
- `play`
- `ended`
- `error`

不得使用 `setTimeout`、CSS 动画时长、滚动位置或按钮点击序列推进课程 Beat。

### `event-registry`

从 `video-event-map.json` 读取事件，负责：

- 判断当前时间是否进入事件窗口；
- 打开、暂停或关闭互动；
- 检查互动是否需要完成；
- 计算返回时间和返回状态；
- 防止向前拖动跳过必需互动；
- 允许回看但不删除已有局部状态。

### `interaction-adapters`

每类互动必须实现同一个适配接口：

```text
enter(event, snapshot)
render(context)
handleInput(input)
getLocalFeedback()
canResume()
exit(reason)
restore(snapshot)
```

适配器可以实现直接控件、阅读、仿真、空间视图、对话或创作；具体技术选择遵循[互动载体实现矩阵](interaction-surface-implementation-matrix.md)。适配器不能自行控制课程视频，也不能创建自己的全局导航。

### `state-store`

至少保存：

```json
{
  "course_version": "0.1",
  "active_beat_id": "beat_practice",
  "video_time_seconds": 42.5,
  "open_interaction_id": "task_practice",
  "local_state": {},
  "draft_response": null,
  "feedback_state": "shown",
  "resume_state": {}
}
```

`local_state` 和 `draft_response` 可以只存在当前会话。只有评价方案明确要求时，才保存长期证据。

### `recovery-controller`

统一处理：

- 媒体加载失败；
- 互动资源失败；
- 用户关闭互动；
- 浏览器刷新；
- 网络恢复；
- 重新播放；
- 静音、字幕和减少动态；
- 移动端视口切换。

必需媒体失败只能重试、重新加载或阻断推进；不能用静态图、文字脚本或简化互动伪装成正式视频链路。

## 3.1 最小代码接口

技术实现至少应能表达以下类型和接口。字段名可以扩展，但语义不能改变：

```ts
export type CourseState = {
  courseVersion: string
  activeBeatId: string | null
  videoTimeSeconds: number
  openInteractionId: string | null
  localState: Record<string, unknown>
  draftResponse: unknown
  feedbackState: "hidden" | "shown"
  resumeState: Record<string, unknown>
}

export type EventDefinition = {
  beatId: string
  cueSeconds: number
  pauseSeconds: number
  resumeSeconds: number
  interactionId: string | null
  eventClass: "observation" | "exploration" | "judgment"
  evidenceRequired: boolean
  completionCondition: string
  requiredAssetIdentifiers: string[]
  retryPolicy: {
    maxAttempts: number
    actions: string[]
    onExhausted: "block_progression"
  }
  resumeState: Record<string, unknown>
}

export interface InteractionAdapter {
  enter(event: EventDefinition, snapshot: CourseState): void
  render(context: unknown): void
  handleInput(input: unknown): void
  getLocalFeedback(): unknown
  canResume(): boolean
  exit(reason: "completed" | "closed" | "failed"): void
  restore(snapshot: CourseState): void
}
```

`CourseRuntime` 只允许通过 reducer 更新状态：

```ts
dispatch({ type: "VIDEO_TIME_UPDATED", seconds })
dispatch({ type: "OPEN_EVENT", beatId, interactionId })
dispatch({ type: "LOCAL_FEEDBACK", value })
dispatch({ type: "CLOSE_INTERACTION", reason: "completed" })
dispatch({ type: "RESTORE_SNAPSHOT", snapshot })
```

组件不得直接修改 `activeBeatId`、`videoTimeSeconds` 或课程完成状态；只能派发事件，由 `CourseRuntime` 决定是否接受。

## 3.1.1 事件图最小契约

`video-event-map.json` 至少包含以下字段；字段使用 JSON 的 snake_case，TypeScript 类型使用 camelCase 映射：

```json
{
  "schema_version": "1.1",
  "video_element_id": "course-video",
  "media_source": "./media/course-video.mp4",
  "duration_seconds": 480,
  "cue_tolerance_seconds": 0.25,
  "timeline_mapping": {
    "mode": "composed_single_file",
    "main_timeline_identifier": "mainline",
    "completed_event_seek_policy": "restore_completed_state_without_reopening",
    "branch_return_policy": "return_to_declared_global_resume_seconds"
  },
  "resource_admission": {
    "course_entry": {
      "required_asset_identifiers": ["video_main", "runtime"],
      "checks": ["present", "loadable", "playable", "runtime_ready"],
      "failure_policy": "retry_or_block"
    },
    "event_entry": {
      "checks": ["present", "loadable", "runtime_capability"],
      "failure_policy": "retry_or_block",
      "degraded_path": false
    }
  },
  "events": [
    {
      "beat_id": "beat_practice",
      "timeline_identifier": "mainline",
      "clip_identifier": "clip_question",
      "media_source_identifier": "video_main",
      "global_offset_seconds": 0,
      "cue_seconds": 42,
      "pause_seconds": 42,
      "resume_seconds": 42,
      "interaction_id": "task_practice",
      "event_class": "judgment",
      "required_asset_identifiers": ["scene_interaction_q01"],
      "evidence_required": false,
      "completion_condition": "local_feedback_shown",
      "retry_policy": {
        "max_attempts": 3,
        "actions": ["retry_load", "reload_event", "reenter_event"],
        "on_exhausted": "block_progression"
      },
      "resume_state": {
        "scene_id": "s01",
        "audio": "restore",
        "captions": "restore",
        "objects": "restore"
      }
    }
  ]
}
```

`completion_condition` 只描述本地互动完成条件，不等于学习目标掌握；`evidence_required` 只有评价方案要求记录学习证据时才设为 `true`。未完成必需互动时不能由 `video.ended` 或播放百分比直接推进。

## 3.2 视频时钟实现要求

事件时间字段全部使用主视频文件的绝对秒数，且必须满足：

```text
0 <= cue_seconds <= pause_seconds <= resume_seconds <= duration_seconds
```

`cue_seconds` 是事件可被识别的时间，`pause_seconds` 是事件要求暂停的时间，`resume_seconds` 是互动结束后的返回时间；它们不是互动内部相对时间。事件按 `cue_seconds` 升序排列，必需窗口和相邻边界按 `video-led-web-course.md` 核对；`cue_tolerance_seconds` 只用于检测。`timeline_mapping.global_offset_seconds` 只用于分段媒体映射，不改变页面运行时的主时间语义。

向前拖拽遇到未完成的必需事件时，运行时必须回到该事件的 `pause_seconds`；回看已完成事件时，按 `completed_event_seek_policy` 恢复已完成状态或重新打开供复习，但不得重复创建学习记录。

推荐实现顺序：

```ts
import { attachPresentationClock, AtmosphereController, placeAnchor }
  from "./video-presentation-runtime.js"

// spec/approvedAssets 已按呈现契约绑定，背景未启用时不创建 controller。
const atmosphere = spec.atmosphere.enabled
  ? new AtmosphereController(document.querySelector("#course-atmosphere"), spec, approvedAssets)
  : null
let lastPresentation = null
const renderPresentation = sample => {
  lastPresentation = sample
  atmosphere?.apply(sample, runtime.worldStateIdentifier, {
    reduced: matchMedia("(prefers-reduced-motion: reduce)").matches
  })
  for (const track of spec.anchors) {
    const node = document.querySelector(`[data-presentation-anchor="${track.identifier}"]`)
    const placement = placeAnchor(node, track, sample, spec.source_dimensions,
      video.getBoundingClientRect(), document.querySelector("#scene-objects").getBoundingClientRect())
    runtime.setSameObjectAccessibleEntry(track.identifier,
      !sample.accurate || placement?.fallbackRequired === true)
  }
}
const disposeClock = attachPresentationClock(video,
  seconds => runtime.dispatch({ type: "VIDEO_TIME_UPDATED", seconds }),
  renderPresentation)

video.addEventListener("seeking", () => {
  runtime.handleSeeking(video.currentTime)
})
// ResizeObserver、motion preference 与 world state 变化时，用 lastPresentation 重绘；
// seeking 中只接受 invalidate；卸载时 disposeClock()/atmosphere?.dispose()。
```

按[呈现契约](video-presentation-contract.md)复制模块、绑定资源与提供非精确同对象入口。`timeupdate/currentTime` 不注入精确呈现通道；frame callback 不直接推进课程。回放、seek、恢复重建 epoch，暂停/互动冻结呈现相位。所有实际推进判断统一进入 `CourseRuntime`，不能在监听器里直接显示下一场景。

## 3.3 异步互动和重复触发

互动适配器如果有加载、仿真或保存等异步动作，必须带有 `interaction_id` 和递增 `request_token`。关闭互动、切换事件或恢复快照后，旧请求返回不得修改当前状态。事件进入、退出和完成动作必须幂等；同一个 `beat_id` 在同一版本中只能有一个活动实例。

## 4. 页面和事件绑定

页面至少包含：

```html
<main id="course-stage">
  <section id="scene-media">
    <video id="course-video" data-media-clock="course">
      <track kind="captions">
    </video>
  </section>
  <section id="task-layer" aria-live="polite"></section>
</main>
```

约束：

- 页面只能有一个课程主视频时钟；
- `scene-media` 是主场景；
- `task-layer` 只承载当前事件的局部互动；
- 互动入口必须绑定 `beat_id`、`interaction_id` 和视频时间窗；
- 互动关闭后恢复原视频时间、字幕、声音、焦点和局部状态；
- 不增加课程目录、永久工作台、独立任务中心或脱离场景的全局互动目录。

## 5. 标准实现顺序

### A. 冻结设计契约

先完成：

- `design-outline.md`
- 按序排列的 Beat ID
- 视频事件时间窗
- `scene-interaction-plan.json`
- 每个事件的进入、暂停、完成、返回和失败策略

没有这些内容，不开始搭建复杂组件或生成正式媒体。

### B. 先做最小媒体时钟

只实现：

1. 视频加载；
2. 播放、暂停、回看；
3. `timeupdate` 事件匹配；
4. 一个事件暂停；
5. 一个互动完成后精确返回；
6. 刷新后恢复同一事件。

这一步通过后，才增加 3D、仿真、阅读层或复杂视觉。

### C. 按事件增加互动适配器

每增加一个互动，必须填写：

```text
beat_id
interaction_id
入口对象
学习者动作
局部反馈
完成条件
视频暂停策略
返回时间
返回状态
关闭/失败策略
键盘与触摸等价
```

没有局部反馈或明确返回状态的互动，不进入实现。

### D. 增加资源准入和恢复

在课程入口和每个事件入口分别检查视频、字幕、音频、互动资源和版本。失败时展示真实的重试/恢复操作，并记录事件 ID、资源版本、重试次数和恢复位置。

### E. 做响应式和可访问实现

至少验证：

- 桌面宽屏；
- 窄桌面；
- 手机竖屏；
- 手机横屏；
- 键盘焦点；
- 触摸输入；
- 字幕；
- 静音；
- 减少动态；
- 高对比度和文字放大。

## 6. 不允许的实现方式

- 用 `setTimeout` 或 CSS 动画代替视频课程时钟；
- 每个互动组件自行维护课程进度；
- 把互动全部写进一个不可追踪的巨大 HTML 文件；
- 用按钮点击直接跳过必需视频事件；
- 用静态占位图冒充已通过的视频媒体；
- 只完成正常路径，不实现错误、刷新、回看和恢复；
- 用一次 `ended` 或播放百分比标记学习完成；
- 通过全局任务列表、永久工作台或独立页面脱离当前场景；
- 先生成大量页面，再反向寻找课程目标。

## 7. 交付等级

| 等级 | 最低要求 | 可以声明 |
|---|---|---|
| `design_draft` | 纲要、事件表、互动计划和风险 | 已完成设计草稿 |
| `prototype` | 可播放样例、一个真实互动、局部恢复、静态检查 | 已完成技术原型 |
| `runtime_candidate` | 全部事件接线、资源准入、错误/刷新/回看、响应式和浏览器记录 | 已完成候选实现 |
| `interaction_complete_prototype` | 已确认完整设计；全目标/Beat、知识矩阵、全部非视频资产、两视口全路径、视觉门及独立 Demo 确认 | 已完成完整学生端 Demo；分镜模式仍保留正式视频差额 |
| `functional_accepted` | 正式媒体、浏览器全路径、无障碍、桌面/手机和版本证据 | 已通过功能验收 |

没有达到对应等级，不得使用更高等级的交付名称。

`prototype` 与 `runtime_candidate` 是局部技术工作等级，不是生产清单的正式终点。前者按所选范围交付技术样例；后者只有通过[完整 Demo 契约](knowledge-surface-and-demo-contract.md)才能映射到 `interaction_complete_prototype`。分镜事件与真实视频的适用运行检查由[前端契约](frontend-prototype-contract.md)定义。

## 8. 验收证据包

`verification.md` 必须分列：

1. 静态结构检查；
2. 运行时契约检查；
3. 浏览器实测；
4. 正式媒体检查；
5. 人工设计审阅；
6. 真人试学；
7. 未执行项目。

视频网页至少记录：

```text
validate_video_led_runtime.py 的命令与结果
video-event-map 与实现版本
course-video 的媒体文件哈希
每个 Beat 的实际进入/暂停/返回结果
错误、刷新、回看、字幕、键盘、触摸和手机结果
截图或 DOM/运行时采集记录
```

结构校验通过只能证明契约一致，不能替代浏览器操作、真人听审或学习效果评价。
