# 真题数据源配置

## 优先级

1. **awesome-ruankao 本地资料库**（最高优先，直接 read）
2. **xiaomabenten/system_architect** (GitHub)
3. **zaonai/system_architect** (Gitee)
4. **xxlllq/system_architect** (GitHub)
5. **ltwmt/system_architect** (Gitee)
6. **Web搜索兜底**

---

## 源0: wujiaming88/awesome-ruankao (GitHub) ⭐⭐⭐（最高优先）

- **API**: `gh api repos/wujiaming88/awesome-ruankao/contents/{path}`
- **分支**: `main`
- **覆盖**: 9个科目，2020-2025年，67个Markdown文件 + 1个PDF
- **特点**: 内容已验证、纯Markdown可直接web_fetch、含完整答案解析
- **访问方式**: `gh api` 获取 `download_url` → `web_fetch` 下载内容

### 访问示例
```bash
# 列出系统架构设计师年份目录
gh api "repos/wujiaming88/awesome-ruankao/contents/真题/系统架构设计师" --jq '.[].name'

# 获取某年份文件列表
gh api "repos/wujiaming88/awesome-ruankao/contents/真题/系统架构设计师/2024年下半年" --jq '.[].name'

# 获取文件下载链接
gh api "repos/wujiaming88/awesome-ruankao/contents/真题/系统架构设计师/2024年下半年/综合知识.md" --jq '.download_url'
# 然后 web_fetch 该URL获取Markdown内容

# 列出其他科目
gh api "repos/wujiaming88/awesome-ruankao/contents/真题" --jq '.[].name'
```

### 目录结构
```
真题/
├── 系统架构设计师/          ← 最完整（6年三科）
│   ├── 2025年上半年/       综合知识.md + pdf/
│   ├── 2024年下半年/       综合知识+案例分析+论文
│   ├── 2024年上半年/       综合知识+案例分析+论文
│   ├── 2023年下半年/       三科齐全
│   ├── 2022年下半年/       三科齐全
│   ├── 2021年下半年/       三科齐全
│   └── 2020年下半年/       三科齐全
├── 信息系统项目管理师/      2024(两批次)+案例分析
├── 软件设计师/              2024(上下)
├── 网络工程师/              2023-2024(4学期)
├── 信息安全工程师/          2023-2024
├── 数据库系统工程师/        2023-2024
├── 系统集成项目管理工程师/  2023-2024
├── 系统分析师/              2023-2024
└── 网络规划设计师/          2023-2024
模拟题/                      模拟试卷
论文/                        万能模板+范文
案例分析/                    解题框架
docs/备考攻略/               学习路线+技巧
docs/政策与考试指南/          2025-2026政策、机考改革
资源/                        教材书单、视频课程
```

---

## 源1: xiaomabenten/system_architect (GitHub ⭐3900+)

- **API**: `gh api repos/xiaomabenten/system_architect/contents/{path}`
- **分支**: `main`
- **真题目录**: `03、历年真题(2009年-2025年)+答案解析`
- **论文目录**: `04、论文（真题范文+写作）`
- **案例目录**: `06、案例分析 新大纲`
- **年份格式**: `2009年下半年` ~ `2025年上半年（回忆版）`
- **特点**: 按年份整理，目录结构清晰，可直接按年份检索
- **局限**: 真题文件多为 PDF（图片扫描），需下载查看

---

## 源2: zaonai/system_architect (Gitee，国内快)

- **API**: `curl -s "https://gitee.com/api/v5/repos/zaonai/system_architect/contents/{path}"`
- **分支**: `master`
- **真题目录**: `03、历年真题(2009年-2025年)+答案解析`
- **论文目录**: `04、论文（真题范文+写作）`
- **模拟题**: `05、模拟题`
- **冲刺资料**: `07、考前冲刺资料`
- **机考模拟**: `09、机考讲解及模拟`
- **特点**: 最全面，含模拟题+冲刺+机考模拟+报名流程

---

## 源3: xxlllq/system_architect (GitHub ⭐8300+)

- **API**: `gh api repos/xxlllq/system_architect/contents/{path}`
- **分支**: `master`
- **真题目录**: `3. 历年真题及解析【2009-2025年】`
- **论文目录**: `4. 论文【真题范文+模板】`
- **特点**: 最权威，含视频教材和讲义，CSDN博客有逐题解析
- **CSDN解析**: https://blog.csdn.net/xxlllq/article/details/85049295
- **局限**: 真题以图片和外部链接形式存储，不可直接读取文本

---

## 源4: ltwmt/system_architect (Gitee，备用)

- **API**: `curl -s "https://gitee.com/api/v5/repos/ltwmt/system_architect/contents/{path}"`
- **分支**: `master`
- **真题目录**: `03、历年真题+答案解析`
- **真题视频**: `05、历年真题视频讲解`
- **案例分析**: `06、案例分析 新大纲`
- **模拟题**: `07、模拟题`
- **特点**: 含真题视频讲解，适合视频学习

---

## Web 搜索兜底

当所有仓库都找不到时，使用 web_search：

### 推荐站点（可抓取）

| 站点 | URL | 适用内容 | 可抓取性 |
|------|-----|----------|----------|
| 博客园 | cnblogs.com | 综合知识、案例分析 | ✅ 好 |
| 信管网 | cnitpm.com | 项目管理类真题 | ✅ 好（部分需登录）|
| 环球网校 | hqwx.com | 综合知识题目 | ✅ 好 |
| 51CTO题库 | t.51cto.com | 在线做题 | ✅ 好 |
| IT顾问 | itgu.com | 论文真题 | ✅ 好 |
| 七巧编程 | qicoder.com | 论文真题 | ✅ 好 |

### 不推荐站点（难抓取）

| 站点 | 问题 |
|------|------|
| CSDN | 全站521反爬，需Googlebot UA绕过且不稳定 |
| 知乎 | 403封禁爬虫 |
| 希赛网 educity.cn | 引流页，实际内容在PDF下载后 |

### 搜索模板
```
{科目名} {年份} {科目类型} 真题 答案 解析
site:cnblogs.com {科目名} {年份} 真题
site:cnitpm.com {科目名} {年份} 真题
```

---

## 知识领域映射

| 知识领域 | 关键词 | 常考科目类型 |
|----------|--------|-------------|
| 软件架构设计 | 架构风格、ABSD、DSSA、ATAM、SAD | 综合+案例 |
| 设计模式 | 23种GoF、创建型、结构型、行为型 | 综合+案例 |
| 质量属性 | 可用性、性能、安全性、可修改性、效用树 | 案例（必考） |
| 数据库 | 规范化、ER图、NoSQL、Redis、MongoDB | 综合+案例 |
| 信息安全 | 加密、PKI、数字签名、访问控制 | 综合 |
| 计算机网络 | TCP/IP、VPN、防火墙、HTTP | 综合 |
| 新技术 | 云原生、微服务、大数据、AI、区块链、边缘计算 | 综合+论文 |
| 软件工程 | 需求工程、UML、测试、DFD | 综合+案例 |
| 分布式系统 | 分布式锁、一致性哈希、CAP、消息队列 | 案例 |
| 项目管理 | 进度、风险、成本、挣值 | 综合 |
| 法律法规 | 知识产权、著作权、标准化 | 综合 |
| 数学算法 | 图论、概率、组合 | 综合 |
| 专业英语 | 技术英语阅读 | 综合 |

## 科目类型

| 科目 | 代号 | 说明 |
|------|------|------|
| 综合知识 | choice | 75道单选题，150分钟 |
| 案例分析 | case | 问答题，1必答+4选2，90分钟 |
| 论文 | essay | 4选1，摘要300字+正文2200字，120分钟 |
