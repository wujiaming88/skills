---
name: deep-investment-research
summary: "系统化投研能力中枢 — 7类研究框架 + 9红线 + 深度研究5步法 + 七棱镜 + 非对称赔率 + 多源一手数据采集。纯研究，不发交易信号。"
---

# Deep Investment Research

把"做一份高质量投资研究"沉淀成可复用的方法论 + 多源一手数据采集工具。

## 能做什么

7 类研究框架：宏观 / 行业 / **公司研究（看懂生意）** / 个股深度研究（投资判断）/ 政策 / 投资可行性 / 风险 / 投资规划。

研究内核：9 条研究红线 · 命门变量聚焦（2-3个+70%火力）· 深度研究5步法（A事实→B推断→C市场定价检查→D含义）· 七棱镜多维扫描 · 反共识引擎 · **非对称赔率**（上下比+期望值+敏感性测试）· 反证5问 · 质量门控。

数据采集：SEC EDGAR / HKEX / AKShare（含 AH比价/LPR/Shibor/北向南向/ETF/新股/龙虎榜等客观数据点）/ FRED / 政策门户。

## 定位

**纯研究**——产出判断、依据、风险、赔率结构与可选路径，支持决策；不做盯盘 / 交易信号 / 交易执行。

## 怎么开始

触发后先读 `SKILL.md`，它会按课题类型路由到 `methodology/` 下对应框架。

## 依赖

`python3`；数据脚本按需装 Python 包（yfinance/akshare/fredapi 等）+ 可选 API key（FINNHUB_API_KEY/FRED_API_KEY，未设置则跳过该源）；联网搜索优先用 web-search-plus/tavily skill，未装则降级内置 web_search。

## 许可

MIT
