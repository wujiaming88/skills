# deep-investment-research

系统化投研能力中枢 —— 一套可复用的投资研究方法论 + 多源一手数据采集工具，作为 OpenClaw Agent Skill 使用。

## 这个 skill 是什么

把"做一份高质量投资研究"沉淀成可复用的方法论与工具，覆盖七类研究：

- 宏观研究（中国 / 美国）
- 行业深度研究
- 个股深度研究
- 投资可行性分析
- 政策研究与追踪
- 风险分析
- 投资规划

内置：**9 条研究红线**、**深度研究 5 步法**（A 事实 → B 推断 → C 市场定价检查 → D 含义）、**七棱镜多维扫描**（宏观/政策/地缘/产业链/资金面/新闻情绪/标的自身）、**6 个专题框架** + **5 个研究模板**、**8 个重点行业的一手源清单**，以及一组数据采集脚本（SEC EDGAR / HKEX / AKShare / FRED / 政策门户等）。

> 定位：**纯研究**。产出判断、依据、风险与可选路径，支持决策；不做盯盘 / 交易信号 / 交易执行。

## 怎么用

触发任意投资研究请求后，先读 `SKILL.md`，它会引导：

1. 读内核 `methodology/research-core.md`（红线 + 研究设计 + 七棱镜 + 5 步法 + 反证 + 质量门控）
2. 按课题类型读对应框架 + 模板（见 `SKILL.md` 表格）
3. 用 `methodology/source-registry.md` 定位行业一手源，取真实数据
4. 按 `methodology/content-reading-protocol.md` 全文阅读、来源回溯，再下结论

## 依赖

**必需**
- `python3`

**数据采集脚本（可选，按需）**
- Python 包：`yfinance`、`akshare`、`fredapi`、`requests`、`beautifulsoup4` 等（按所用脚本安装）
- API key（按需，未设置则自动跳过该数据源）：`FINNHUB_API_KEY`、`FRED_API_KEY`

**联网搜索（可选，软依赖）**
- 优先使用 [web-search-plus](https://clawhub.ai) / [tavily-search](https://clawhub.ai) skill（覆盖好、可控）
- 未安装时自动降级用 OpenClaw 内置 `web_search` 工具

## 可配置环境变量（均带默认值，不设也能用）

| 变量 | 作用 | 默认值 |
|------|------|--------|
| `RESEARCH_OUTPUT_DIR` | 研究报告归档目录 | `~/research-output` |
| `TRADING_ROOT` | 数据采集落盘目录 | `~/research-data` |
| `SEARCH_SKILL_PATH` | 联网搜索脚本路径 | `~/.openclaw/skills/web-search-plus/scripts/search.py` |

## 目录结构

```
deep-investment-research/
├── SKILL.md                      # 入口：触发条件 + 9 红线 + 用法
├── methodology/                  # 方法论
│   ├── research-core.md          # 内核（所有研究通用）
│   ├── source-registry.md        # 8 行业一手源清单 + 搜索优先级
│   ├── content-reading-protocol.md
│   ├── {industry,stock-deep-dive,feasibility-analysis,policy-research,risk-analysis,investment-planning}.md
│   ├── {china-macro,us-macro}.md
│   └── templates/01-05*.md       # 5 个研究模板
└── scripts/                      # 多源一手数据采集（可选）
```

## 许可

MIT，见 [LICENSE](./LICENSE)。
