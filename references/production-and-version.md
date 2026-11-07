# 两次确认、当前文件与真实证据

复制[生产清单2.0](../assets/production-manifest.template.json)。清单保存事实，不编造确认人、记录或验收。版本2.0沿用真实授权原则，当前不解析历史视频/考核/Demo合同。

## 阶段与确认

current_status依次为design_draft、design_confirmed、representative_confirmed、production_complete、functional_accepted、learner_trial_complete。最后一项仅在真实走访实际执行且获授权时使用。没有独立全课Demo、成绩或效果评分阶段。

approvals保留追加历史，条目包括approval_identifier、kind（design或representative）、confirmed_by、confirmed_at、subject_sha256、evidence_identifier。active_design_approval与active_representative_approval只引用真实当前确认。记录可追溯原始审阅证据，脚本不认证人的身份；明确Agent/脚本自签不能充当人类确认。

- design指纹由scene-plan.learning的规范化内容生成，含具体规则、台词、事件、互动和接续。改变这些含义时重开受影响设计。普通实现修复、源代码改动、光照数值、排版和新增检查记录不改变设计指纹，仍须适当复验。
- representative指纹含当前设计指纹、共用表现约定、所选场景视图与真实候选文件/证据快照。代表场景属于成品范围，候选入口/依赖和审阅证据冻结保留；扩展全课不覆盖已确认候选，也不拿候选检查冒充当前全课验收。保持约定的其他场景扩展不用重签；改变已确认画风/声音身份等约定时重确认对应范围。

`validate_production.py --fingerprints`只计算待审subject，不自动写确认。`--previous-manifest`检查确认历史完整前缀；它不证明外部身份，也不自动回放所有历史课程。版本说明与原记录保留，既有课不自动迁移。

## 当前文件与证据

files逐项登记file_identifier、path、content_sha256和role（entry/source/resource/reference），覆盖当前入口、全部声明源码和实际资源。实际磁盘内容与快照一致。代表候选放独立不可覆盖路径，candidate_files登记相同结构；候选范围与当前构建分别核对。

evidence逐项有evidence_identifier、kind、path、content_sha256。确认使用human_confirmation；命令用command_run；实际参与用cua_operation；其他审阅用content_review、visual_review、motion_review、audio_review、performance_review或experience_trial。记录文件本身也有SHA256，内部引用的截图/日志/音频等产物逐项核对。

checks逐项有check_identifier、domain、scene_identifiers、status、evidence_identifiers、scope。status为pending、passed、failed、blocked或superseded（保留已替代记录，不计当前覆盖）。domain为content、visual、motion、interaction、accessibility、recovery、performance、audio或rule。确认代表场景时检查所选代表范围；最终交付时content/visual/motion/interaction/accessibility/recovery/performance覆盖全部必需场景。有声场景额外audio；声明executable规则时其制作测试必须实际执行。观察场景的interaction域检查查看/接续与控制，不制造答错重做。

内容/画面/动作/声音/性能及操作收据须绑定当前runtime_digest（当前文件ID/路径/实际哈希的规范化摘要），并记录覆盖场景、实际结果与产物。代表候选检查绑定candidate文件摘要；规则命令收据按[验收](validation.md)绑定实际输入与完整日志。补截图/日志不会改变design指纹；修改源代码使旧运行证据过期。结构记录和实际观察分开，空文件或笼统passed不能代替完整证据类型。

```bash
python3 "<skill-root>/scripts/validate_production.py" production-manifest.json --plan scene-plan.json --fingerprints
python3 "<skill-root>/scripts/validate_production.py" production-manifest.json --plan scene-plan.json --previous-manifest previous.json
```

校验器不执行任意计划中的命令；先由执行者运行适当制作检查，再登记真实收据。当前数据字段没有默认审批权限；发布、付费与外部写入仍依实际授权。
