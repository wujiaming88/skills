# Skills

面向 AI Agent 的技能集合：把开发、研究、写作、设计和运维中的可复用方法，整理成可读取的操作流程、参考资料与配套脚本。

当前收录 **19 个 Skill，分为 6 类**。每个 Skill 保持独立的顶层目录；本页按主要用途分类，不改变安装路径。点击名称可查看对应的 `SKILL.md`。

## 分类导航

| 分类 | 数量 | 适用任务 |
| --- | ---: | --- |
| [开发与界面设计](#development) | 4 | 编码规范、工程质量、变更验证、前端需求落地 |
| [内容与演示](#content) | 4 | 报告转文章、模板风格 PPT、小红书文案与封面 |
| [图像与可视化](#visuals) | 5 | 模型生图、图片编辑、架构图、网页高清截图 |
| [研究与投资分析](#research) | 1 | 宏观、行业、公司、政策与投资风险研究 |
| [教育与考试](#education) | 3 | 高考志愿建议、软考真题检索、论文练习 |
| [OpenClaw 运维与可靠性](#operations) | 2 | 运行诊断、性能分析、长时 Cron 任务验收与恢复 |

[安装与使用](#usage) · [组合使用示例](#combinations) · [目录约定与维护](#maintenance)

<a id="development"></a>

## 开发与界面设计

| Skill | 主要用途 | 选择提示 |
| --- | --- | --- |
| [karpathy-coding-guidelines](./karpathy-coding-guidelines/SKILL.md) | 用明确假设、简单实现、局部修改和可验证目标，减少 AI 编码中的常见偏差。 | 适合需要轻量编码准则的开发、修复和审查任务。 |
| [software-engineering-discipline](./software-engineering-discipline/SKILL.md) | 对维护型代码约束改动范围、抽象程度、接口契约、迁移安全与风险测试。 | 面向需要持续维护的项目；强调真实 API 与实际执行证据。 |
| [test-code-change](./test-code-change/SKILL.md) | 从变更影响和失败风险出发制定并执行验证，报告覆盖、缺口与残余风险。 | 用于已授权代码变更或明确要求的测试验证审计，不用于普通仓库浏览。 |
| [translate-ui-intent](./translate-ui-intent/SKILL.md) | 把“简洁、紧凑、高级感”等模糊意图转成可实现的界面决策，并做视觉验证。 | 已有产品优先沿用设计系统；可交付设计契约，也可用于界面实现。 |

<a id="content"></a>

## 内容与演示

| Skill | 主要用途 | 依赖或边界 |
| --- | --- | --- |
| [report2article](./report2article/SKILL.md) | 将研究报告、周报编辑为读者文章，或优化既有文章的结构、表达和配图。 | 以双清单和全文语义核对保留事实、来源及限定；同时避免标题过碎与层次缺失，不代替新增研究。 |
| [ppt-from-template](./ppt-from-template/SKILL.md) | 从参考 PPT/PDF 提取视觉风格，用 PptxGenJS 重新生成演示文稿。 | 需要样式参考及外部 `pptx` Skill、PptxGenJS、Python/转换工具；不是直接修改原 PPT。 |
| [xhs-content-forge](./xhs-content-forge/SKILL.md) | 将技术长文或选题改为小红书笔记包：标题、正文、配图清单、标签与封面变量。 | 内置“五岳 AI 虚拟公司”过程纪实定位；不负责自动发布，配图可交给下方 Skill。 |
| [xhs-cover-maker](./xhs-cover-maker/SKILL.md) | 按固定品牌版式制作小红书封面、要点图和金句卡。 | 使用 HTML/CSS、WeasyPrint、Poppler 与 Pillow 渲染；品牌和版式有预设，不是通用创意设计器。 |

<a id="visuals"></a>

## 图像与可视化

| Skill | 主要用途 | 依赖或边界 |
| --- | --- | --- |
| [custom-imagegen](./custom-imagegen/SKILL.md) | 通过自定义 OpenAI 兼容接口生成、编辑图片，支持多图输入、遮罩与 JSONL 批量任务。 | 需配置服务地址、模型和凭据；实际能力取决于服务端。支持先做 dry run。 |
| [nova-canvas](./nova-canvas/SKILL.md) | 通过 AWS Bedrock 调用 Amazon Nova Canvas 生成图片。 | 需要 AWS 凭据与模型访问权限；本 Skill 不处理图片编辑或视频生成。 |
| [stable-image-ultra](./stable-image-ultra/SKILL.md) | 通过 AWS Bedrock 调用 Stable Image Ultra 或 Stable Diffusion 3.5 Large 生图。 | 适合照片、插画等视觉素材；需要对应模型权限，不适合精确文字图表。 |
| [svg-architecture-diagram](./svg-architecture-diagram/SKILL.md) | 用 SVG 绘制架构、组件、流程与数据流图，保留明确标签和连接线。 | 使用 HTML/SVG 与 Playwright 渲染；适合结构和文字必须准确的技术图。 |
| [web-render-screenshot](./web-render-screenshot/SKILL.md) | 将 HTML 页面、界面原型、数据图表或信息图渲染为高清 PNG/JPEG。 | 使用 Playwright/Chromium；重点是结构化页面与可读文字，不是模型生图。 |

**怎么选：** 照片或插画按已配置的模型服务选择生图 Skill；需要改图或接自定义接口时看 `custom-imagegen`；精确架构关系用 `svg-architecture-diagram`；文字、表格和 UI 导出用 `web-render-screenshot`；固定小红书品牌图用 `xhs-cover-maker`。

<a id="research"></a>

## 研究与投资分析

| Skill | 主要用途 | 依赖或边界 |
| --- | --- | --- |
| [deep-investment-research](./deep-investment-research/SKILL.md) | 提供宏观、行业、公司、个股、政策、可行性、风险与投资规划的方法论及一手数据采集脚本。 | 数据源按任务配置，部分需要 API 凭据；聚焦研究，不做盯盘、交易信号或交易执行。 |

<a id="education"></a>

## 教育与考试

| Skill | 主要用途 | 依赖或边界 |
| --- | --- | --- |
| [gaokao-zhiyuan](./gaokao-zhiyuan/SKILL.md) | 根据目标省份当年规则、考生位次和历年官方录取数据，整理冲稳保建议与志愿草表。 | 需要省份、科类、分数、位次及偏好；按省份现查规则，建议不等于录取保证。 |
| [ruankao-questions](./ruankao-questions/SKILL.md) | 按考试科目、知识领域、年份及题型检索软考真题并整理答案和来源。 | 优先使用指定资料仓库，再做外部检索；具体年份与题型覆盖以来源实际内容为准。 |
| [ruankao-essay](./ruankao-essay/SKILL.md) | 按系统架构设计师论题与子问题生成结构化练习稿，并检查段落要素和字数。 | 用于备考练习；自动构造的项目背景应视为模拟案例，不是真实经历。 |

<a id="operations"></a>

## OpenClaw 运维与可靠性

| Skill | 主要用途 | 依赖或边界 |
| --- | --- | --- |
| [openclaw-diagnostics](./openclaw-diagnostics/SKILL.md) | 从日志和会话文件分析 Run 时间线、推理耗时、Token、工具调用及错误。 | 依赖本地 OpenClaw 数据与 Bash/Python；高级模式涉及配置与重启，使用前需另行审查和授权。 |
| [cron-run-reliability](./cron-run-reliability/SKILL.md) | 为复杂、长时 isolated Cron 提供有界等待、产物检查、恢复顺序与证据化收口。 | 仅针对子任务/文件交接或多阶段交付；不负责创建调度、执行业务发布，也不应套在简单提醒上。 |

<a id="usage"></a>

## 安装与使用

这些目录包含 Skill 指令与配套资源，**不是一个统一安装的应用，也不会因克隆仓库就自动生效**。先选择具体 Skill，再检查其宿主工具、依赖、外部服务和权限要求；仓库不包含全部外部依赖。

### 在 OpenClaw 中安装单个 Skill

下面以 `report2article` 为例。适用于支持本地目录安装的 OpenClaw 版本，具体选项先用 `openclaw skills install --help` 确认。

```bash
# 获取仓库
git clone https://github.com/wujiaming88/skills.git

# 安装某一个 Skill 到目标 Agent；main 可替换为你的 Agent ID
openclaw skills install ./skills/report2article --agent main

# 查看该 Agent 识别到的 Skill 详情及路径
openclaw skills info report2article --agent main
```

安装后，在请求中说明任务和输入材料；需要明确选用时，可直接写出 Skill 名称，例如：

> 使用 report2article，把这份研究报告改成面向技术读者的文章，保留事实、来源和关键限定。

更新时，先更新仓库，再比较本地已安装副本。**已有同名 Skill 或本地修改时，不要盲目覆盖**；确认要替换后再按 CLI 提示使用 `--force`。检查实际加载路径，避免同名旧副本遮蔽新版本。

### 在其他 Agent 环境中使用

按宿主支持的 Skill 机制加载整个目录，保留 `SKILL.md` 与其引用的资源。Markdown 能被读取，不代表 OpenClaw 专用工具、脚本依赖或模型接口可以直接跨宿主运行；需要逐项核对。

### 运行前检查

- 完整读取所选 `SKILL.md`，按需加载 `references/`、`methodology/` 等材料。
- 安装该 Skill 实际需要的依赖，而不是一次性安装全部技能的依赖。
- 凭据通过宿主的受保护配置、环境变量或凭据管理器提供，不写入仓库、README、聊天或命令参数。
- 需要联网、模型调用、发布或系统修改的步骤，应遵守当前宿主的权限、审批与费用限制；仓库中的默认配置不替代任务授权。
- 旧示例中的模型、价格、年份、路径及平台规则需重新核验。分类目录仅说明用途，不承诺所有脚本已在你的环境验证。

<a id="combinations"></a>

## 组合使用示例

按实际任务选用，不必把每条链路全部跑一遍。

| 目标 | 可选组合 |
| --- | --- |
| 将投研成果转成可读文章 | `deep-investment-research` → `report2article`；需要技术架构图时再加 `svg-architecture-diagram` |
| 把文章拆成小红书内容 | `xhs-content-forge` → `xhs-cover-maker` → 人工发布 |
| 改进现有产品界面并验证 | `translate-ui-intent` + `software-engineering-discipline` → `test-code-change` |
| 将已有内容制作成演示稿 | 准备内容与参考模板 → `ppt-from-template` |
| 排查复杂定时任务交付问题 | `openclaw-diagnostics` 辅助定位 → `cron-run-reliability` 核对当前运行证据 |

<a id="maintenance"></a>

## 目录约定与维护

```text
skills/
├── README.md                 # 分类导航与使用说明
└── <skill-name>/             # 每个 Skill 保持顶层独立目录
    ├── SKILL.md              # 元数据、触发条件与操作流程
    ├── references/           # 可选：参考协议与细化规则
    ├── methodology/          # 可选：研究方法论
    ├── scripts/              # 可选：执行或验证脚本
    └── assets/               # 可选：模板、样式和图像资源
```

上述为示意结构，不要求每个 Skill 包含所有子目录。新增、移除或更名时，同步更新本页分类、数量与相对链接；每个 Skill 在主分类中只列一次，跨领域用途通过选择提示或组合示例说明。

**许可：** 以各 Skill 自身的许可文件和声明为准；例如 [deep-investment-research/LICENSE](./deep-investment-research/LICENSE)。本仓库未声明统一的顶层许可证，不将单个 Skill 的许可外推到全部内容。
