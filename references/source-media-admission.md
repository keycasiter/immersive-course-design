# 输入媒体实检

用户提供或课程继承图片、音频、视频时，在据此判断内容、选择参考或编译制作计划前执行本模块。远端素材先通过授权读取取得本地实际文件；取得失败的输入仍登记为 failed。文档、网页和 3D 的内容读取分别使用对应能力，本模块只校验栅格图片、音频和视频，不把其他类型冒称已解码。

## 执行与完成条件

1. **盘点**：从本轮输入和继承范围列出全部媒体，用稳定 `source_identifier` 对应来源注册记录；登记用途和实际文件。真正没有输入时填 `input_state=not_supplied`，两张表均为空。有输入时填 supplied，`declared_sources` 与 `reviews` 必须逐个对应。完成条件是输入数与来源数一致；检查器不能发现未登记的用户附件，盘点责任仍由执行者承担。
2. **实检**：读取文件 SHA256、实际媒体流和完整解码结果。图片查看实际构图/对象；音频听取目标区间并核对声音和正文；视频观看有关片段，并在动作、信息揭示或转场位置抽帧。样本按 source 分目录，保留抽样时间和源 SHA。完成条件是文件可读可解码，观察来自实际内容；扩展名、尺寸和自动转写均不能单独关闭内容审阅。
3. **记录**：复制 `assets/source-media-review.template.json`。每条 review 的 `status` 为 passed 或 failed；passed 要有本源 SHA、`content_review` 和视频 `frame_samples`。content_review 使用 status/reviewer/bound_sha256/evidence_file/evidence_sha256/observations；证据正文说明实际看/听的范围、对象、动作、内容和限制。failed 保存 `failure_reason`，继续独立工作，阻断依赖该输入的计划和提交。完成条件是没有把取得或探测失败折叠成“无输入”。
4. **检查**：执行 `scripts/validate_media_admission.py source <source-media-review.json> --report <source-admission-validation.json>`。默认重读源和证据 SHA、ffprobe、完整解码，并重新抽取登记时点的标准帧核对样本身份。完成条件是机械检查通过且实际内容审阅覆盖预定用途；抽帧不证明完整观看，机械通过不证明学科内容正确。

输入报告采用 1.0。`declared_sources` 每项为 source_identifier、kind（image/audio/video）、path、content_sha256、purpose；reviews 每项为 source_identifier、status、source_sha256、content_review、frame_samples、failure_reason。证据路径相对本记录所在目录。视频 sample 为 source_identifier、source_sha256、at_seconds、path、content_sha256；时点以文件起点计秒，落在实际视频时长内。

样本必须由检查器同一抽帧函数 `extract_frame` 生成：ffmpeg 输入后 seek，首视频流一帧，宽度最多 640，PNG，固定单线程。可在实际观察后使用该函数保存证据；不能给另一条视频的帧补上本源标识。检查期间只写临时目录，源、证据和原始输入保持不变。

## 传播与边界

媒体计划引用本记录与检查报告，使用到的来源 ID 同参考职责关联；模型槽位身份继续由[媒体任务](media-job-execution.md)拥有。源文件变化重新实检并重查受影响计划、请求和质量证据，保持原报告可追溯。权利、隐私与事实来源继续按生产清单验收，passed 不授予使用权限。

旧课只在授权输入修改范围补检查；缺少本版实检写 unverified，补记录不自动生成媒体。制作侧统计面板可以展示检查进度，准入仍读取原记录、当前文件和实际检查结果。
