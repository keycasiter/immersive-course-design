# 空间学习计划与运行时契约

用于`spatial_native_web`及包含原生空间场景的`hybrid_web`。视频主导仍执行[video_led_web](video-led-web-course.md)；本契约不修改现有课程1.2状态、两道正式确认门及独立澄清/内容/Demo门禁。

## 文件与范围

复制[计划模板](../assets/spatial-learning-plan.template.json)为课程的`spatial-learning-plan.json`。`schema_version=1.0`是此附加计划的版本，不是蓝图版本。它关联真实1.2蓝图的目标、场景、资源和任务；不复制目标/评价正文，不取代课程蓝图或生产清单。

| 区块 | 必需内容 |
|---|---|
| 标识 | course_identifier、course_version与蓝图一致；experience_profile为spatial_native_web或hybrid_web |
| runtime | engine/version；绝对时间与状态求值入口、时钟所有权、历史状态重建、检查点字段、WebGL失败与低动态规则 |
| scenes | scene_identifier、objective_identifiers、media_resource_identifier、task_identifiers；学科/视觉/动作/反馈和回退契约 |
| delivery | 初稿允许空文件/检查列表；正式验收提供真实版本文件SHA256及适用证据域的结果、证据文件SHA256和审阅者 |

每场填写：

- `teaching_job`：本场要看懂/完成什么及为何需要空间表示。
- `representation`：route取procedural/dcc_asset/hybrid；source_of_truth、units、coordinate_system；parameters为有名称、单位、有限min/max/default的列表，可为空；invariants为有稳定ID、statement、source_identifiers和test_reference的非空列表。来源引用蓝图，不把测试脚本当事实来源。
- `presentation`：attention_target、camera_and_projection、structure_and_look、labels_and_units、approximation_boundary。写可实现的形体/材料/光色与必要标签，不能只填“精美”。
- `learning_actions`：稳定action_identifier、task_identifier、target、input、guard、transition_rule、visible_consequence、learning_evidence、feedback_and_retry。无学科任务的示范场景可为空，但learning_action_decision说明它在教学循环中的职责，不能把整课都声明为无动作。
- `continuity`：entry_condition、completion_rule、return_checkpoint。完成条件指向课程任务判定，时间结束不能单独授予掌握；任务允许“补救后继续”时保留受助状态。
- `equivalent_path`：同目标替代任务、键盘路径、reduced_motion、media_failure。静态展示可替代运动观察，但必须保留该目标需要的判断/构造/解释。

参数输入、数值/标签与几何状态共享单一求值源；视觉动画的临时抬起/展开不改变评分模型。不同条件与数值误差必须在内容评审中核对，脚本不评判学科含义。

## 时钟、学习状态与求值

| 状态 | 唯一写入者 | 前进/恢复规则 |
|---|---|---|
| 学习状态 | 课程任务状态机 | scene/task、attempt、证据、帮助、提交/复核结果；依任务规则推进，不由ended/播放百分比推进 |
| 演示状态 | 当前场景求值器 | `evaluate(sceneState, localTime, inputs, seed)`完整求值对象/标签/FX；固定步长仿真或累计效果需检查点或重放，不能只设置t |
| 媒体时钟 | 当前主媒体控制器 | 视频用真实currentTime；有旁白主导的3D段用音频时钟；无音频用连续时基。切换前暂停原所有者，局部解释独立计时 |
| 视图与焦点 | 当前视图/任务控制器 | camera/target/zoom/剖面/选择/焦点可恢复，机位变化本身不算学科进展 |

`renderAt(t)`可用作固定演示轨的导出适配；交互场景要同时指定状态快照和参数。对同一状态/种子/时刻复取应在目标配置下稳定，不能把不同学习者输入硬压成同一帧。同步导出与异步收敛采用相应技术协议，不强套单一截图器。

检查点包含课程/规则/资产版本、当前scene/task、允许的对象参数与状态、演示事件/时间、机位、首答/帮助/修订和焦点。不保存无关身份信息；刷新/返回/WebGL context restore先校验版本，再重建状态。未知版本、缺失媒体或非法参数进入明确恢复路径，不能把已完成标记直接赋给新任务。

学习模式：未达必需任务条件时不靠拖动/章节按钮跳过；允许回看而不清空首答。预览/教师演示/结课回顾可自由seek，明确其模式，不能向学习记录写入伪完成。无障碍支持与正常工具不自动记作答案性帮助。

## 蓝图、清单和校验

沿用蓝图已有`three_dimensional`/`diagram`/`video`及清单`three_dimensional`/`diagram`/`runtime`等kind。`progression`是教学作用，可由三维或图解主媒体承担；主媒体类型和教学作用分别登记。生产清单experience_profile记录所选路线；加入场景计划到evidence_files，并将其设计内容/规则、实际入口/源依赖分别绑定到相应确认指纹，未参与确认的计划不能自动沿用确认。

```bash
python3 "<skill-root>/scripts/validate_spatial_learning.py" \
  "<course-directory>/spatial-learning-plan.json" \
  --blueprint "<course-directory>/course-blueprint.json"
```

正式准出追加`--delivery`。检查标识/版本、场景/资源/目标/任务关联、参数域、必要字段、动作引用及实际文件/证据哈希。五个证据域`subject_rules`、`visual`、`motion`、`runtime`、`equivalent_path`必须passed；有声音时另含audio；无声音写no-audio设计依据。每域可以引用具体报告/测试/截图/片段，需说明覆盖范围；不以一个笼统PASS代表全部域。

此脚本不会运行浏览器、证明视觉达标、执行不变量测试、听审、评判反馈或创建人类确认。原有蓝图/清单联合校验继续执行；实际页面仍用CUA/MCP验收。程序化导出视频要另核对真实媒体/音轨与片段；生成式视频仍按原视频生产计划与验收器执行。

## 与现有运行交付的绑定

复制[空间运行交付模板](../assets/spatial-runtime-delivery.template.json)，沿用runtime_delivery/demo_runtime 1.0的入口、源码、知识矩阵、浏览器证据和资源指纹。新增runtime_mode=`scene_state`，仅供spatial_native_web/hybrid_web使用；兼容字段`event_map_reference`在此模式引用kind=`spatial_learning_plan`的本版计划，该计划带runtime_mode与event_graph_version。HTML以`script#spatial-learning-plan`嵌入完全相同JSON，并声明data-runtime-mode="scene_state"；代码从此数据驱动实际求值/动作，浏览器取证覆盖真实结果。文件自包含输出可能把计划和源码并入同一HTML；计划中的delivery.files登记独立源/资源，避免把含自身哈希的整个HTML再嵌入自身形成循环，最终HTML由外层清单/运行指纹绑定。

demo_contract沿用原知识载体矩阵、目标/路径/桌面与窄屏覆盖、当前文件指纹和人类内容/Demo审阅。原生正式运行另需scene_state、parameter_boundaries、context_restore、deterministic_seek、caption_sync、return_state、responsive_layout、accessibility的实际浏览器路径；混合路线额外验证media_timing/video_bridge。文案/结构检查不能证明代码确实消费计划，实际对象变化和恢复仍需CUA/MCP操作。

设计联合清单校验要求一个当前spatial_learning_plan与蓝图，检查实际文件及引用；这不替课程确认。视频原路线依旧要求video_clock，不能把scene_state作为绕过真实视频验证的开关。无现场角色不虚构口型检查；有声音/角色按实际适用范围验收。

## 改动与兼容

旧课程1.2不因Skill更新自动迁移。新的空间路线或受影响重大改稿填写此计划；路线/规则/任务变化按原依赖使相关确认失效，单纯同约定材质/标注修复按原范围复验。计划校验通过只代表当前结构和证据绑定可核对，不改变课程状态。
