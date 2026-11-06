# Immersive Course Design

面向 Agent 的沉浸式课程 Skill，覆盖教学设计、分镜审阅、学生 Demo、媒体生产、功能验收与学习效果评价。

从学习目标、知识动作和可观察证据推导教学，再设计世界、媒体与互动。课程设计、实现和验收分别记录实际完成范围与版本证据；自动化检查不替代教师确认或真实试学。

设计时按知识难点调用 [学科教学指引](references/subject-pedagogy.md)，覆盖语言与文学、数学、自然科学、人文与实践类内容；通过 [语境知识编织](references/contextual-knowledge-weaving.md)把背景、人物、典故、事件与知识谱系接回学生的判断和修订。

## 安装

克隆到 Agent 支持的 Skill 目录。例如 Trae：

```bash
mkdir -p ~/.trae/skills
git clone https://github.com/keycasiter/immersive-course-design.git \
  ~/.trae/skills/immersive-course-design
```

其他支持 `SKILL.md` 的 Agent 可将整个仓库放入其 Skill 目录，保留相对路径。入口为 [SKILL.md](SKILL.md)。

## 使用

在支持 Skill 的 Agent 中提出课程任务，例如：

- “使用 immersive-course-design，设计一节二年级《登鹳雀楼》课程，先交完整设计稿。”
- “审阅这份教学分镜，检查学生行动、反馈和故事后果是否一致。”
- “评测这个课程 Demo，区分结构检查、实际操作与学习效果。”
- “参考外部课件案例，说明观察层级并提取可复用的互动结构。”

Agent 按任务加载对应执行入口。新课和重大改稿先完成可审设计；后续 Demo、正式生产和试学沿用 Skill 中的真实确认与阶段要求。

## 文件结构

| 路径 | 内容 |
|---|---|
| [SKILL.md](SKILL.md) | 任务派发与阶段入口 |
| [COURSE-PIPELINE.md](COURSE-PIPELINE.md) | 完整课程生产流程 |
| `references/` | 教学、叙事、媒体、评价与验收契约 |
| `assets/` | JSON、Markdown、HTML/CSS/JavaScript 模板与固定声音参考 |
| `scripts/` | 校验器、回归检查和配音工具 |

## 校验

结构校验和常规回归使用 Python 3.10 或更新版本。以下命令在仓库根目录执行：

```bash
python3 -m unittest discover -s scripts -p 'test_*.py'
python3 scripts/check_contract_regressions.py
python3 scripts/check_assessment_integrity.py
python3 scripts/check_execution_flow.py
```

针对课程文件运行相应 `validate_*.py`，参数见脚本 `--help`。模板含待填写字段，不能直接作为已通过验收的课程。

浏览器运行检查需要 Playwright 与浏览器。配音需要另行部署 Qwen3-TTS、模型权重及适配硬件的运行环境，见 [voice-continuity.md](references/voice-continuity.md)。这些依赖按进入的阶段准备。

外部案例与方法引用保留各自来源和观察范围，见 [外部课件参考库](references/external-courseware-reference-library.md)。声音候选的模型、参考文字和校验值记录在 [voice-catalog.json](assets/voice-catalog.json)。
