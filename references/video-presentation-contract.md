# 呈现帧、动态背景与画面锚点

本文件拥有 `video_presentation` 1.0 的数据和接口。视频事件推进、必需窗口读取 `video-led-web-course.md`；背景视觉层读取 `video-surface-contract.md`。动态背景或精确画面锚点触发本文件；无此需求时保持背景关闭。

## 支持范围与实施入口

初版支持已组装的单一主视频时间域、居中 `object-fit: contain`、源视频归一化矩形、线性轨迹、显式遮挡区间，以及静态图的受控低幅缩放。分段/分支时间域、cover 裁切、任意多边形、相机跟踪、自由播放的背景视频不在初版适配器范围；先给出额外映射与实际浏览器验收，不能把初版 PASS 当作支持。

复制[数据模板](../assets/video-presentation.template.json)和[运行模块](../assets/video-presentation-runtime.js)。数据的 `main_video_asset_identifier/main_video_sha256`、解码尺寸和时长绑定当前主视频。完整结构定义由[校验器](../scripts/validate_video_presentation.py)执行。锚点关键帧使用实际采用的视频 PTS，区间端点可以是明确的隐藏/退出边界；结构校验不证明坐标对准对象或时间值来自解码帧。

## 两条时间通道

- 教学位置：`timeupdate/currentTime` → `CourseRuntime`。事件进入、必需任务、回看与 seeking 全部由课程 reducer 决定。
- 呈现帧：有 `requestVideoFrameCallback` 时，仅用 `metadata.mediaTime` → 背景与精确锚点。不得将 currentTime 注入该通道。
- 无帧 API 时：背景可用标明 `accurate=false` 的 currentTime 近似值；精确锚点隐藏，提供同对象的键盘/阅读入口。不能声称帧级验收。
- seeking 开始增加 `epoch`，隐藏旧锚点/背景；新 epoch 的已呈现帧直接重建，不播放过渡。旧回调、异步结果和旧坐标不得回写新状态。同 epoch 的呈现时间不回退。

暂停、互动和帮助保持最后呈现时间；世界状态改变或布局改变时用同一时间重算。刷新保存教学位置和世界状态；重入先 seek，等已呈现帧再显示精确锚点。倍速改变相位推进速度，后台标签页暂停时不补跑独立动画。

## 背景映射

`atmosphere.enabled=true` 时，cues 无空隙、无重叠地覆盖 `[0,duration)`；结束帧取最后 cue。每 cue 有稳定 identifier/scene_identifier、start/end、`motion=ambient_loop|still`、正 cycle_seconds、0–2 秒且不长于 cue 的 transition_seconds，以及 world_state → 正常 asset / still_asset 的映射。跨 cue 混合需要相同世界状态变体。

相位为 `(presented_time - cue.start) % cycle`。首 cue 没有前场景，alpha=1；后续正常跨界线性混合，alpha 为 `(t-start)/transition` 截到 0–1，旧层停在前 cue 的边界相位。seek/replay/restore/故障恢复直接落位，alpha=1。reduced-motion 或背景失败取同场静态，phase=0；静态也失败时隐藏背景保留中性舞台，主视频和学习状态继续。背景是可选体验资产，此规则不改变必需教学媒体的 retry/block 政策。

`AtmosphereController.apply(sample, worldState, {reduced,rebuild})` 返回 cue/asset/phase/alpha。Web Animations 始终暂停，只有 apply 设置 currentTime；不要以 CSS 自动播放、独立视频或墙上时间推进。页面声景由主视频/正式声音契约承担，背景层静音、不接收输入、不推进课程。

## 矩形轨迹与投影

anchors 为可空列表。每项绑定 identifier、beat_identifier、object_identifier、半开时间窗、normalized_source_rectangle、linear、至少两关键帧及 ordered occlusions。x/y/width/height 均在源画面 0–1 域内；关键帧覆盖首末边界，遮挡区间隐藏和禁用入口。

`anchorAt(track,t)` → 源矩形或 null；`projectContain` 按 `min(containerWidth/sourceWidth, containerHeight/sourceHeight)` 投影，加实际 letterbox 偏移。`placeAnchor` 将视频 DOMRect 投入 overlay 坐标域，同时设置 hidden/disabled。原始源比例、暂停态视频缩小、手机竖横屏、缩放和 ResizeObserver 都必须重投影，不能直接把源坐标写成页面百分比。矩形热区的命中区域保持绑定；触摸目标不足时用明确的同对象入口，不能扩到邻近对象而声称精确命中。

参与计划的 `scene_anchor.presentation_anchor_reference` 引用 `presentation_reference#anchor_identifier`；`data-presentation-anchor` 标记 DOM 入口。fallback 保留同对象、相同知识动作与学习状态。

## 接线和准出

1. 将 JSON 注册为 `evidence_files.kind=video_presentation_contract`，在 `demo_runtime/runtime_delivery.presentation_reference` 引用；正常/静态背景资产进入 bound_asset_identifiers。运行模块进入源码/资产指纹。
2. 页面 `data-atmosphere="synchronized"` 标记已启用同步背景，unused 时为 `none`；精确入口有 data-presentation-anchor。联合检查拒绝已标记但缺少呈现引用的运行包。
3. 先运行 `validate_video_presentation.py <json> --video <main.mp4>` 读回主视频字节、尺寸、时长（容差为一帧或 50ms 的较大值），再与实际 event map 时长、Beat 和所有背景资产联合核对。锚点参与计划另运行 `validate_scene_interaction_plan.py <plan> --event-map <map> --presentation <json> --presentation-reference <registered_reference>`；联合检查要求锚点被同对象、同 Beat 的参与计划引用。
4. 浏览器采集路径 `atmosphere_sync` 与 `anchor_projection` 按适用性执行；每条覆盖 desktop/narrow。背景另覆盖 normal/reduced，并实际操作暂停、互动、seek、replay、恢复、倍速与背景故障。每条测试保存实际 artifact 与 runtime_fingerprints。
5. 运行[呈现回归](../scripts/check_video_presentation.py)验证模块能力；它是合成材料的通用回归，不能代替真实课程。内容/体验效果还需教师走课和学习者试用。

采集独立主视频 PTS/呈现参考与实际应用日志，保存 cue、asset、world revision、phase、alpha、epoch、viewport、motion preference 和主视频/运行/素材指纹。应用延迟 50ms、源 PTS 2ms、相位 20ms 仅为默认工程预算；按实际帧率、设备与误差来源说明，不能把声明字段当成像素、GPU 性能、体验吸引力或学习效果的证明。

## 旧评测接口兼容边界

本版入口是 `contract_version=1.0`、`main_video_sha256` 和嵌套 `atmosphere.cues`。旧 M17 runner 的顶层 cues、schema_version 和首 cue 从零开始混合的规则属于旧协议；旧回归只证明旧范围。当前课程直接执行上方随包校验与采集，不把新 JSON 送入旧通道或继承旧 PASS。

迁移旧采集必须明确转换字段、独立 PTS、首 cue/普通转场/rebuild、world-state、故障和近似时钟，并以实际 controller 输出重新绑定指纹。Web Animations 的 playState=paused 是正常驱动方式，视觉相位是否随 apply 更新另查；accurate=false 不允许精确锚点通过。氛围增量与真实沉浸测量按[沉浸评价](immersion-evaluation.md)另执行。
