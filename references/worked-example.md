# 实施示例：同一张纸怎样拼直

示例展示“语义 → 规则 → 状态 → 场景消费者 → 验证”的交接。它包含[完整计划](../assets/examples/area-reassembly/scene-plan.json)、[几何规则](../assets/examples/area-reassembly/rules.mjs)、[状态adapter](../assets/examples/area-reassembly/adapter.mjs)和[可运行测试](../assets/examples/area-reassembly/rules.test.mjs)。没有完整Three.js页面、实际声音、确认或课程验收记录；`index.html`、`src/main.mjs`和Three版本为拟定工程接口，进入真实制作时核对并实现。

## 从内容到具体经历

| 项目 | 本例落实 |
|---|---|
| 内容 | 平移保持面积，矩形宽高对应原平行四边形的底与垂直高 |
| 情境/视点 | 几何工作桌，正交俯视，纸片及基准线可完整看见 |
| 初次进入 | “沿虚线分开，再把斜纹的一角移到另一边。”底6、高4与直角符号同时可见 |
| 参与/回应 | 先分开，再水平移动三角形；中途看空缺/重叠，终点看到无缝矩形与面积说明 |
| 保留与结束 | 两块纸保持身份，基准线不动；可复位、重看或随时退出，无作答门槛 |

本例不宣称对齐某教材，来源是下方可核对的数学推导。换题材时重新选取情境与机制，保留单一规则、完整求值和实际呈现的工作方法。


## 学习者画面怎样逐步展开

| 时刻 | 当前可见重点 | 按需内容 |
|---|---|---|
| 刚进入 | 同一张纸、底高必要标线与“沿线分开”的邀请 | 来源、完整推导与全局工具 |
| 已分开/平移 | 可移动三角形、原位置与当前缺口/重叠；操作时保留纸片与反馈同屏 | 操作帮助或原形对照 |
| 拼合端态 | 无缝矩形、与原底高的对应；这时出现面积结论 | 完整数学推导 |
| 查看推导后返回 | 恢复当前纸片位置、视点与焦点 | 阅读位置保留，不重置经历 |

这些状态沿原事件与对象实现；事实正文仍来自计划。按[页面与注意力](page-and-accessibility.md)安排显隐，不把整份可读主稿常驻在场景旁，也不删去证明/原文来换取少字。

## 数学依据

设底 `b>0`、高 `h>0`、顶部右移 `0<s<b`。原顶点为 `(0,0),(b,0),(b+s,h),(s,h)`；沿 `x=s` 分出左侧三角形 `(0,0),(s,0),(s,h)`，余块顶点为 `(s,0),(b,0),(b+s,h),(s,h)`。三角形仅平移 `(b,0)`，不缩放旋转。

在任意高度 `y=t*h, 0≤t≤1`，余块横截面为 `[s,b+s*t]`，平移后三角形为 `[b+s*t,b+s]`，恰好组成 `[s,b+s]`。因此端态是宽b、高h的矩形，无重叠或缺口；分割与平移保持面积，原面积为 `b*h`。这说明该受限模型的关系；推广到任意倾斜量需要另选分割，不能把本例范围外的图形硬套进生成器。

## 文件与接口怎样对应

| 计划/语义 | 可执行部分 | 真实课程仍要实现 |
|---|---|---|
| `paper`、`rule_area` | `geometry({base,height,shear,offset})` 返回纸块顶点、标签锚点及面积，范围外抛错 | 用相同顶点更新Three几何，厚度朝背面，不改变数学表面 |
| `cut_paper`、`slide_corner`、`reset_paper` | `createPaperAdapter(paint).act`检查前置状态、约束offset并返回完整对象patch | Pointer射线与纸面求交，键盘/按钮统一调用同一动作，决定控件可用性 |
| 场景端态与标签 | `evaluate`每次从当前状态完整求模型，交给`paint(model,paper,state)` | 更新网格/世界矩阵后投影DOM标签，再呈现说明；不单独缓存第二套坐标 |
| `event_rectangle` | 控制器仅在主应用调用`markEvent`时记录 | 矩形和说明真实呈现后回报；中途拖动、调用act或文件存在都不能当完成 |
| 重看与恢复 | reset恢复对象初态；snapshot/restore恢复对象与事件历史 | 恢复视点、焦点、DOM与资源；终场退出由应用处理 |

`paint`按`paper.phase`选择未切原形、分块或拼合端态，不能同时画出原形实物和两块分片；原形对照若需要则另用清晰虚线。

`geometry`不负责像素投影，`paint`不负责改教学规则，控制器不负责验证offset的学科范围。恢复时应用adapter也要核对本课自定义状态；通用控制器只验证通用合同/ID等条件。

一次有效接线可沿 `slide_corner → adapter.act → state.objects.paper.offset → geometry → paint → renderer/DOM → 实际呈现后markEvent` 追踪。`evaluate`是同步求值回调，构造控制器时也会调用；不要在其中引用尚未完成赋值的控制器或递归标记事件。

## 在本地实际运行

从Skill根目录执行，派生文件写入临时目录：

```bash
python3 scripts/validate_experience.py assets/examples/area-reassembly/scene-plan.json
python3 scripts/compile_experience.py assets/examples/area-reassembly/scene-plan.json --out /tmp/area-reassembly-derived
node --test assets/examples/area-reassembly/rules.test.mjs
```

校验核对字段、引用与范围；编译生成实际可读主稿和ID索引；测试核对多个合法形状/端态的面积与接缝、非法输入、标签模型值，以及真实控制器的动作/恢复接线。测试中的`paint`只是数据接收回调，`markEvent`是受控的测试调用，均不是渲染或交互取证。

## 做到成品还缺什么

进入制作后，用真实锁文件更新版本，完成Three网格、相机、灯光、页面与`paint`，把DOM与命中统一到最终世界变换。重点看切缝深度/闪烁、三角形平移身份、直角/底高标签、目标视口可读与拖动反馈；按[空间制作](spatial-production.md)修正。

制作检查中实际运行规则测试并用`run_check.py`记录输入与日志。再按[验收](validation.md)操作首动作、拖动/键盘、复位/返回、缩放、低动态及中断恢复；源码、真实文件、确认和证据登记到本课生产清单。例子结构通过不代表这些工作已完成。
