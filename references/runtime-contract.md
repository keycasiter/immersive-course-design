# 实时场景、参与与恢复

Three.js负责渲染/命中/对象动画，应用负责世界规则与场景状态。scene-plan提供同一对象/事件/互动标识，运行不能各写一套标签、数值或几何近似。可复用[轻量控制器](../assets/scene-runtime.mjs)，应用实现其adapter，不强制具体前端框架。

## 分开状态职责

| 状态 | 内容与写入者 |
|---|---|
| 体验状态 | 当前场景、实际已呈现事件、对象状态、自然选择/对话与可选查看；应用控制器依世界规则接续，不维护成绩/掌握率 |
| 演示时钟 | 当前场景/局部声音的连续时间；有主导音频时与其同步；tick或seek不自动完成必需事件 |
| 视图 | 相机/target/zoom/剖面/选择、阅读位置和焦点；切换视图本身不表示理解 |
| 音频 | 用户操作后启用，暂停/局部对话/恢复有唯一所有者，避免叠音 |

adapter.evaluate(state)完整绘制该状态的对象/标签/显隐/人物/FX/字幕；adapter.act(action,payload,state)返回实际对象/视图变化。事件只能在实际呈现/操作完成后由应用markEvent，不能一进入就标记全部完成。需要历史的仿真按固定种子/步长重放或检查点重建；不能只设time uniform。

## 控制器接口

createExperienceController(plan, adapter)提供getState、act、markEvent、continueTo、tick、seek、pause、snapshot、restore。adapter可实现evaluate、act、captureView、restoreView和onSceneEnter；实际Three网格/DOM/声音由这些回调接通。纯控制器单元测试不证明画面或命中已实现。

控制器检查已声明动作/目标、当前场景事件和允许接续，保留可选探索状态；渲染回调不会自动推进。apply返回的对象状态须序列化，不保存DOM/网格实例；语义场景/事件由控制器拥有，adapter不能直接写分数或场景完成。自然选择可改变对象或局部状态，再依已声明事件继续。

检查点含合同/体验版本、当前scene/time、已呈现事件、对象/对话与视图状态；restore先核对版本与合法ID再重建，同一输入/种子/时刻应稳定。恢复以暂停状态落地，声音由用户继续，未知版本或破损状态提供明确回到可安全入口的选择，不悄悄套用旧经历。

## 页面与失败

主页面用语义main承载Three场景，有可访问的对象控制/阅读和同内容替代入口。模态仅在需要时使用；静态校验不强制固定区域或CSS名称。WebGL丢失/resize/横竖屏先保留状态，再重建资源/投影/标签并恢复；同一对象的坐标、命中与文字安全区同步更新。

真实应用测试关注inspect/approach/viewpoint/follow/manipulate/dialogue/choose/read中实际使用的类型，及返回、重看、静音、低动态、键盘/触摸和中断恢复。没有判分任务，不要求incorrect/help/revision路径。控制器对话状态是自然互动，不是考试首答锁定。
