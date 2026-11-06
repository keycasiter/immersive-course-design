# 媒体任务运行与恢复

图片、视频、3D和配音共用此运行契约。工具名与本地请求指纹不代表提供方支持幂等、取消或去重；先查当前官方接口或实际返回。

每个任务保存到课程工作目录的 job 记录，字段至少包括：
复制 `assets/media-job.template.json` 建立本次记录，所有状态按实际返回填写。

`schema_version`、`job_identifier`、`asset_identifier`、`asset_version`、`request_sha256`、`provider`、`provider_task_identifier`、`phase`、`attempts`、`terminal_phase`、`source_registry_references`、`output_paths`、`output_sha256`、`output_attempt_identifiers`、`cost_status`、`actual_cost`、`budget_limit`、`retry_limit`、`last_error`、`recovery_action`。

每个 attempt 记录 attempt_identifier、开始/结束时间、请求指纹、提供方任务 ID、状态、费用、错误与输出标识。终态只能为 accepted、failed、cancelled 或 timed_out；accepted 输出必须能反查产生它的 attempt。课程决定和可听正文分别引用 `decision-registry.json` 与 `utterance-registry.json` 的稳定 ID 和版本，不在 Job 中复制第二份权威正文。

请求指纹使用 `request_sha256`。对实际模型、参数、台词/提示词、参考文件哈希和输出约定计算；身份 token、私有 endpoint、个人路径不写入可分发记录。重做质量改变参数或参考时登记新请求，不复用旧任务成功结论。

## 提交前读回（Job 1.1）

新任务使用 Job 1.1；`active_attempt_identifier` 指向本次尚未提交的 attempt。每个 attempt 保留自己的 `request_sha256` 与 `submission_readback`，复制 `assets/media-submission-readback.template.json` 作为填写结构。旧 1.0 任务保留原结果和恢复信息，缺失读回写 unverified；补记录不触发重生成。

1. **编译**：由已验证适配器形成真正要提交的 JSON 参数快照，保存完整提示和有序参考。台词以当前权威注册表为准，导演/发音说明与正文分开。完成条件是请求可直接用于本次调用，参数与能力有依据。
2. **读回**：从该快照提取实际模型、参数、完整提示、输出文件名与实际 slot→文件→用途→SHA。生成 `reference_manifest` 时引用生产计划的真实参考，实际传入的文件再次核对。完成条件是所有实际槽位都有对应，登记的参考确实传入。
3. **比对**：使用 `scripts/submission_contract.py` 的 `normalize_request` 得到 `normalized_request`，用 `canonical_digest` 重算 attempt 的 `request_sha256`，同步 active job 指纹。`expected_contract` 从当前计划与权威台词推导 `production_contract_sha256`；每个可听事件的 `utterance_bindings` 绑定原 ID、版本和正文 SHA。原生台词的 `prompt_start/end` 为 JSON 解码后提示正文的 Unicode 字符半开区间，逐字符相等；外配台词不冒称原生提交正文，两个位置填 null。完成条件是实际请求与本版意图逐字段一致。
4. **关口**：视频调用前执行 `validate_video_production.py --pre-submit --unit <实际单元ID>`。它重读文件并重新计算，不信任手填 passed。检查通过后读取同一快照完成实际调用；发送前再次核对快照 SHA、参考 SHA 与当前契约，任一改变重新检查。完成条件是采用已检查内容发送，保存实际提供方回执；校验报告自身不是受理回执。
5. **验收**：真实返回后核对台词、声音、对象、动作与教学内容。完成条件由对应媒体验收 owner 定义，请求一致不代表生成正确。

`submission_readback` 的权威结构为模板中的字段。`reference_manifest` 的每项为 reference_identifier、kind、slot、purpose、path、content_sha256。`normalized_request` 由适配器导出，canonical JSON 采用 UTF-8、sort_keys、无额外空白、ensure_ascii=false、禁止非有限值；唯一指纹算法由 `submission_contract.canonical_digest` 实现。语义指纹排除个人路径，原始序列化文件 SHA 则证明采用同一份内容。`production_contract_sha256` 只覆盖当前单元的请求与所引用台词版本/内容；无关台词变化不强制重做已验收资产。

当前读回适配器 `trae_generate_video_v1` 读取 `{"tool":"functions.GenerateVideo","arguments":{实际工具字段}}`，槽位为 `image_paths[0]`、`video_paths[0]` 等。仅支持工具声明的字段；没有模型选择或音频参考参数，模型填 unknown，声音文件不能伪绑到图片槽位。接口/提供方变更时先更新适配器和回归；无法提取的关键字段标 unverified 并阻断该正式提交路径，不猜测后端语法。

本地完整参数证据与公开展示分开；认证头、私有签名和上传句柄不放入公共材料。上传句柄型提供方须实现从实际句柄到本地文件 SHA 的映射后才准入。检查失败只阻断受影响任务；已受理或已生成仍按下表恢复，不增加逐镜确认。

| 阶段 | 恢复动作 |
|---|---|
| planned / preflight | 检查权限、输入、权重、存储、预算和算力；失败不提交 |
| submitting | 请求未返回任务ID但可能已受理时先查历史；不能盲目重复提交 |
| queued / running | 保存原任务ID；按提供方建议查询，支持通知时等待通知，避免睡眠轮询 |
| generated / downloading | 输出已生成，下载失败只重试下载原输出；不重新生成 |
| downloaded | 校验文件、哈希、解码和元数据；坏下载重新取原结果 |
| quality_review | 内容或连续性不合格才登记质量重做，使用新尝试与预算记录 |
| cancelled / failed / timed_out | 区分本地超时与服务终止；先查原任务及计费，再决定续取、取消或重做 |
| accepted | 实际质量、治理、等价路径和版本证据均成立后准出 |

## 已选资产复用与完整性

相同课程约定下优先复用已验收的实际输出。复用是本地采用操作，沿用产生它的原 Job、attempt、请求和输出 SHA；保存 `assets/asset-reuse.template.json` 的 1.0 记录，不创建虚构的提供方任务、生成尝试或新计费回执。

1. **匹配**：按当前模型/工具/适配器版本、完整请求、真实参考内容、台词权威版本和输出格式判断适用性。路径变更不改变内容，文件名/格式约定仍属于实际请求。完成条件是当前采用意图与原输出依据相符，旧 SHA 或同名路径不能直接视为命中。
2. **读回**：原 Job 必须 accepted，选中输出反查唯一 attempt，重读原 `submission_readback`。本版视频计划和台词用既有 `expected_contract` 重算，核对请求与台词 bindings；所需参考文件缺失或变化即失败。完成条件是当前契约成立，原 attempt 仍可追溯。
3. **恢复**：执行 `validate_media_admission.py reuse <asset-reuse.json>`，重算源输出、Job、计划与审阅文件 SHA，完整解码并核对格式。目的文件已存在且内容不同则阻断。通过后可复制到临时文件，核对 SHA，以不覆盖现有文件的方式发布；再加 `--materialized` 检查实际目的文件。完成条件是采用文件与原验收资产字节一致。工具只校验，不自动复制、提交或付费调用。
4. **复验**：登记当前教学用途和相邻接续的实际审阅；接入后继续当前媒介的完整质量与运行验收。完成条件是复用身份与当前适用性分别通过，旧课程的通过记录不代替新接续验收。

`source_output_path` 必须与原 Job 的 output_paths 条目完全一致，相对该 Job 所在目录解释。其余路径相对复用记录解释。`current_production_contract_sha256` 由 `submission_contract.expected_contract` 得出；`reuse_review` 与输入 owner 的 content_review 使用相同证据结构，但绑定实际输出。视频单元继续指向原 Job 和采用 attempt，`asset_reuse_file` 指向复用记录；复用记录绑定本版计划 SHA，计划只保存该路径，避免循环指纹。采用新目的路径时，现有 `--delivery` 自动执行该记录的 materialized 身份检查；当前时间线、声音、质量与浏览器检查仍全部执行。

当前机械实现只接纳 Job 1.1、视频计划 1.2 和现有视频适配器的 `reuse_selected_asset`。其他媒介按原始 provenance 与当前质量人工核对，缺少适配器的机械身份检查写 unverified，不能冒称本命令通过。

自动生成缓存只在确定性转换已被实际适配器验证时启用，键包含工具/版本、所有声明输入的内容 SHA、参数与输出格式。提供方 seed 只是请求参数；原生随机生成以“复用已选资产”处理，不能由 seed 推断重复请求可复现或提供方幂等。dry-run 只报告，不恢复文件、不更新缓存。缓存缺失、损坏或下载失败先恢复原任务/输出；质量重做继续原预算和尝试规则。历史原费用单列，不把它当本次节省金额。

预算和重试上限由项目/单课明确配置；未知费用单列 unknown，不猜余额。达到上限保存可恢复任务及原因，等待必要的预算或服务条件；不自动加费。不支持取消时说明任务可能仍在执行，不能伪称已取消。

共享GPU以设备、任务与占用记录协调。加载前查询当前进程和可用显存；不终止他人任务。并发只在测过显存余量和输出独立时启用，OOM先释放本任务资源并降并发，再重查原任务。长任务使用后台通知，不重复启动已运行命令。

配音脚本支持 `--batch-file` 的 JSON 列表，每项为 voice_id、text或text_file、output、可选seed；一次加载模型，逐条保存完整 WAV/JSON。参考prompt缓存按模型文件指纹和参考SHA256区分；无缓存也不逐句启动模型。输出锁与GPU占用分别管理。

配音发布使用临时文件、WAV解码验证、JSON提交回执和异常回滚。两个文件不能跨文件原子重命名；消费者仅在同名JSON含 publication_status=complete、输出哈希一致且 generation-status=complete 时使用。突然断电可能留 publishing 状态或锁，恢复时核对原输出、临时备份与进程，不能当成成品或自动覆盖。
