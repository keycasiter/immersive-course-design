# Immersive Course Design

设计与制作以 Three.js 实时场景承载的沉浸式学习。学习者通过观察、探索、视点、对话和对象操作理解具体内容。

安装时保留整个目录与相对路径，从 [SKILL.md](SKILL.md) 开始。主链路是：内容依据 → 完整体验设计 → 设计确认 → 代表成品场景 → 代表场景确认 → 全量制作 → 真实验收。设计、局部修复和维护任务按入口路由进入相应范围。

| 需要什么 | 阅读入口 |
|---|---|
| 当前该做哪一步 | [任务与阶段地图](SKILL.md) |
| 每步怎样做、产出什么、何时收口 | [生产流程](references/production-workflow.md) |
| 怎样写可感知内容和自然参与 | [体验设计](references/experience-design.md) |
| 怎样把计划接到规则、状态和代码 | [完整实施示例](references/worked-example.md) |
| 怎样判断成品可用且品质成立 | [真实验收](references/validation.md) |

空间技术可协同 [threejs-anime-short](https://github.com/keycasiter/threejs-anime-short)，课程不要求 GLB、Blender 或预渲染影片。普通动画制作由该技术 Skill 独立负责。

## 生产文件的职责

`scene-plan.json`拥有生产期体验语义、表现约定与实现配置；`experience.md`和运行索引由编译器派生；`production-manifest.json`独立保存当前文件、真实确认与验收。纯设计尚无工程时先交完整可读主稿，不虚构实际实现。详见[数据归属](references/contract-ownership.md)。

`references/`提供按阶段/问题读取的方法，`assets/`包含模板、状态控制器、实施例子与声音参考，`scripts/`提供编译、结构核对、证据绑定及命令记录。

## 本地验证

需要 Python 3 与 Node.js；课程运行的 Three.js 版本由各工程锁定。

```bash
python3 scripts/validate_experience.py assets/examples/area-reassembly/scene-plan.json
python3 scripts/compile_experience.py assets/examples/area-reassembly/scene-plan.json --out /tmp/area-reassembly-derived
python3 -m unittest discover -s scripts/tests -p 'test_*.py'
node --test scripts/tests/runtime.test.mjs assets/examples/area-reassembly/rules.test.mjs
```

这些命令验证方法工具与示例，不自动证明真实课程画质、声音自然、交互可用或学习效果。示例只实现规则与状态接线，页面入口与渲染仍属拟定接口。

当前合同保持 2.0；旧视频/考核流程由 Git 历史保存，不自动迁移旧课程。既有声音参考保留原样，使用前核对来源、权利和授权。
