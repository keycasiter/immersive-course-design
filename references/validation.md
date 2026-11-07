# 真实验收：内容、画面与参与

制作验收检查交付成果；学生体验不被安排成考试。静态合同、真实命令、原尺寸画面、连续动作、CUA操作、声音和真实走访分别记录范围。

## 四个品质面与制作证据

| 关注面 | 实际检查 |
|---|---|
| 看得清 | 重要对象、字/公式、空间关系和远近主次；目标视口/设备阅读与遮挡 |
| 结构成立 | 比例、厚度/连接、中层、材料/光照、必要学科规则与演示近似 |
| 参与自然 | 观察、靠近/查看、视点、对话/操作的回应；人物、声画、事件和返回接得上 |
| 运行舒适 | 运镜有信息任务，无不必要眩晕；当前设备的操作、声音、加载/性能和恢复 |

规则声明executable时执行真实制作测试；source_review规则仍核对来源。用[命令记录器](../scripts/run_check.py)保存原退出码、输入哈希与完整日志；它只记录真实运行，不证明测试充分或学科理解。日志不能代替实际视觉审阅。

```bash
python3 "<skill-root>/scripts/run_check.py" --record review/rules.json --bind src/rules.mjs --bind tests/rules.test.mjs -- node --test tests/rules.test.mjs
```

## 证据文件

内容/画面/动作/声音/性能审阅收据有kind、runtime_digest、scene_identifiers、result、reviewed_by、observed_result及artifacts（每项path、content_sha256、kind）。写实际所见所听和适用条件；不以空文本或统一PASS当观察。音频实际听审并关联音频产物，帧/波形或文件存在不能证明自然。

cua_operation另外记录tool=cua或mcp、target_url、captured_at、device_identifier、实际viewport和actions；每项有kind、target_identifier、observed_result，执行计划内互动时加interaction_identifier。动作类型按本课实际参与选择，可用enter、inspect、approach、viewpoint、follow、manipulate、dialogue、choose、read、return、replay、restore、keyboard、touch、mute、reduced_motion、resize或context_restore。制作者验收覆盖已承诺互动；学习者无需全点热区。检查引用对应互动/对象，不制造答错或分数。

command_run引用run_check.py实际JSON，包含command/cwd/时间、execution_status、原exit_code、input_snapshots、inputs_unchanged及日志哈希；它绑定实际相关源码/测试输入而非整份画面摘要。制作清单把它关联声明规则。校验器不根据字段名称执行任意代码，也不把合成单元fixture当真实课程证据。

## 真实画面与全量覆盖

交付页面在当前允许的CUA/MCP中实际查看并操作目标视口；不采系统整屏或无关应用。导出帧、接触表和录屏可作作品审片证据，不冒充播放器/对象操作已执行。通道故障、锁屏或设备不可用时具体记录未覆盖，继续独立可做检查，不能宣布相应范围通过。

按实际存在的参与检查目标可达、自然响应、退出返回、重看、键盘/触摸、视图/阅读位置、静音/低动态与资源失败/恢复。场景/动作覆盖由scene-plan派生；可选热区不需要全部打卡，必需内容与当前承诺参与必须可用。桌面和手机是否必需由当课target_devices决定，承诺的设备逐一实际核对。

代表场景查所选闭环；最终查所有必需场景、相关视口/模式与当前源码。局部修改查受影响部分，整合和交付才扩大范围。语义、审美、性能和真实学习感受没有统一自动分数，报告实际入口、版本、通过范围、缺口和已关闭问题。
