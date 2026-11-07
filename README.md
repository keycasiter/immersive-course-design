# Immersive Course Design

以Three.js实时场景承载体验驱动的沉浸式学习。学习者通过观察、查看、换视点、第一人称参与、对话和行动理解内容。

入口：[SKILL.md](SKILL.md)，阶段速查见[制作索引](COURSE-PIPELINE.md)。安装时保留整个目录的相对路径。需要空间制作时协同[threejs-anime-short](https://github.com/keycasiter/threejs-anime-short)；课程不要求GLB、Blender或预渲染影片。普通动画制作仍由技术Skill独立负责。

## 2.0结构

- `scene-plan.json`：体验语义、表现约定和实现配置的唯一机器来源。
- `experience.md`与运行索引：由编译器派生，便于审阅和实现，避免重复写互动正文。
- `production-manifest.json`：当前文件、真实确认与实际验收证据，独立于设计语义。
- `references/`：按问题读取的设计、制作与治理方法。
- `assets/`：计划/清单模板、轻量状态控制器、声音参考。
- `scripts/`：编译、静态核对、证据绑定与实际命令记录。

```bash
python3 scripts/validate_experience.py path/to/scene-plan.json
python3 scripts/compile_experience.py path/to/scene-plan.json --out path/to/derived
python3 scripts/validate_production.py path/to/production-manifest.json --plan path/to/scene-plan.json
python3 -m unittest discover -s scripts/tests -p 'test_*.py'
node --test scripts/tests/runtime.test.mjs
```

这些检查不自动证明画质、声音自然、实际交互或学习效果。真实验收见[validation.md](references/validation.md)。当前版本移除了视频专用与练习/考试流水线；原版保留在Git历史，不自动迁移旧课程。现有声音参考原样保留，使用前核对来源、权利和当前授权。
