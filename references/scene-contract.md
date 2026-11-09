# 场景计划2.0：唯一语义来源

复制[场景模板](../assets/scene-plan.template.json)，跨文件职责见[归属表](contract-ownership.md)。schema_version为2.0、profile为threejs_experience，旧课程合同不自动迁移。标识使用稳定英文名称，所有引用在本计划解析。正文和动作只维护一处，`compile_experience.py`派生experience.md及scene-index.json；派生文件不另行改写教学内容或填通过记录。

## 设计稿与实现声明的区别

纯设计请求可先交可读完整稿；场景计划是进入生产后的结构化来源。当前2.0校验要求完整 `implementation`，尚未有工程时不要以虚构的实际版本/文件声称生产计划已落地。用户要求提前交结构化设计时，可将实现区作为明确标注的拟定接口，并在外部交接表记录待实现状态；后续创建工程时核对真实锁文件与入口，更新计划。结构有效不表示这些文件已经存在，文件真实性由生产清单验证。

全部规则（包括 `source_review`）都有 `rule_bindings`；全部互动都有 `bindings`，范围须与声明精确对应。`compile_experience.py`生成的运行索引只有ID与接续，不能替代含实际语义的完整计划传给控制器。具体填法见[实施示例](worked-example.md)。

## 字段归属

| 区块 | 内容与适用规则 |
|---|---|
| experience_identifier/version | 本课身份与包版本；包版本不能代替真实内容指纹 |
| learning | 标题、学习者背景、体验承诺、理解关注点、来源/内容清单、对象/人物/规则、实际场景与接续、等价路径；设计确认覆盖这个区块 |
| presentation | 共用画风、结构/材料/光照、视点/文字安全区、目标设备、人物表现和逐场观察机位；代表场景确认覆盖共用约定与所选场景视图 |
| resources | 实际图片/纹理/声音/字体/资料，可为空；包含resource_identifier、kind、file、purpose与governance（source、rights、privacy、disclosure、retention、equivalent_path） |
| implementation | Three精确版本、真实入口/源码文件、互动绑定、规则绑定、求值/动作/快照/恢复接口、时钟及资源生命周期 |

场景有required、content/object/character引用、实际orientation、see/hear/relationship、events、interactions和progression。初次场景补最小背景；后继场景说明交接，不重复长开场。required_content以来源和用户范围拆出，全部必需项由可达的必需场景覆盖；不按固定场景数量判断完整。

## 人物、对象与规则

人物条目含character_identifier、identity_basis、fictional、source_identifiers、participation及introduction（text、trigger、anchor）。虚构人物可无史实引用，但明确创作边界；真实身份依据须有来源。presentation.character_profiles按实际人物填form_and_identity、voice_reference（资源ID或null）、speech_and_motion，旁白不伪造人物。

对象有meaning、source_identifiers、rule_identifiers。规则含rule_identifier、statement、source_identifiers、verification（source_review或executable）和test_check_identifier。只有真实需要验证的学科/几何/机制关系才声明规则，不为过检查制造公式；executable规则关联真实执行收据，内容正确仍需审阅。变形、数值和标签共用同一规则实现。

## 参与与接续

interaction.kind取inspect、approach、viewpoint、follow、manipulate、dialogue、choose或read。条目明确目标、邀请/可发现入口、实际response、visible_consequence、发出的事件和accessibility_equivalent。自然对话不设标准答案，自然选择不判分。观察场景可无互动，但整课至少有真实可参与入口。

事件有稳定ID、实际trigger、visible_change及可空sound_resource_identifier。progression列可前进场景、当前必需事件和理由；仅真正承载内容的事件才限制接续，不把可选热区全点完当条件。允许自由查看、退出和回来，重看不伪造经历记录或分数。

实现bindings为每项互动提供可定位入口与handler；rule_bindings为声明规则提供source_file与export_name。计划描述不证明代码已消费它，实际绑定和运行通过[验收](validation.md)验证。画面、可读主稿与学习语义的对应由相同ID和当前内容指纹核对。

```bash
python3 "<skill-root>/scripts/validate_experience.py" scene-plan.json
python3 "<skill-root>/scripts/compile_experience.py" scene-plan.json --out derived
```

结构有效只说明引用/字段/范围一致，不判定剧情自然、语境充分、质感或学生真实感受。当前模型不包含题目、练习、评分或考试字段；制作检查是作者检查，不转为学生考核。
