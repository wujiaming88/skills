# 真题数据源配置

## GitHub 仓库

### 源1: xxlllq/system_architect（⭐8300+，最权威）
- **API**: `gh api repos/xxlllq/system_architect/contents/{path}`
- **真题目录**: `3. 历年真题及解析【2009-2025年】`
- **论文目录**: `4. 论文【真题范文+模板】`
- **分支**: `master`
- **特点**: 真题以图片和外部链接形式存储，CSDN博客有详细逐题解析
- **CSDN解析**: https://blog.csdn.net/xxlllq/article/details/85049295

### 源2: xiaomabenten/system_architect（⭐3900+，结构最好）
- **API**: `gh api repos/xiaomabenten/system_architect/contents/{path}`
- **真题目录**: `03、历年真题(2009年-2025年)+答案解析`
- **论文目录**: `04、论文（真题范文+写作）`
- **案例目录**: `06、案例分析 新大纲`
- **分支**: `main`
- **年份子目录**: `2009年下半年` ~ `2025年上半年（回忆版）`
- **特点**: 按年份整理，目录结构清晰，可直接按年份检索

## Gitee 仓库

### 源3: zaonai/system_architect（CTO说，内容最全）
- **API**: `curl -s "https://gitee.com/api/v5/repos/zaonai/system_architect/contents/{path}"`
- **真题目录**: `03、历年真题(2009年-2025年)+答案解析`
- **论文目录**: `04、论文（真题范文+写作）`
- **模拟题目录**: `05、模拟题`
- **冲刺目录**: `07、考前冲刺资料`
- **年份子目录**: 同源2结构
- **特点**: 最全面，含模拟题和冲刺资料

### 源4: ltwmt/system_architect
- **API**: `curl -s "https://gitee.com/api/v5/repos/ltwmt/system_architect/contents/{path}"`
- **特点**: 备用源，结构类似

### 源5: deven01/system_architect
- **API**: `curl -s "https://gitee.com/api/v5/repos/deven01/system_architect/contents/{path}"`
- **特点**: 备用源，结构类似

## Web 搜索（兜底）

当仓库中未找到目标内容时，使用 web_search 搜索：
- 搜索模板: `系统架构设计师 {年份} {科目} 真题 {知识点}`
- 有效站点: CSDN、知乎、博客园
- 示例: `系统架构设计师 2024下半年 综合知识 真题 设计模式`

## 知识领域映射

| 知识领域 | 关键词 | 科目 |
|----------|--------|------|
| 软件架构设计 | 架构风格、ABSD、DSSA、ATAM | 综合+案例 |
| 设计模式 | 23种GoF、创建型、结构型、行为型 | 综合+案例 |
| 数据库 | 规范化、ER图、NoSQL、Redis | 综合+案例 |
| 信息安全 | 加密、PKI、数字签名、访问控制 | 综合 |
| 计算机网络 | TCP/IP、VPN、防火墙 | 综合 |
| 新技术 | 云原生、微服务、大数据、AI、区块链 | 综合+论文 |
| 软件工程 | 需求工程、UML、测试 | 综合+案例 |
| 质量属性 | 可用性、性能、安全性、可修改性 | 案例 |
| 项目管理 | 进度、风险、成本 | 综合 |
| 法律法规 | 知识产权、著作权、标准化 | 综合 |
| 数学算法 | 图论、概率、组合 | 综合 |
| 专业英语 | 技术英语阅读 | 综合 |

## 科目类型

| 科目 | 代号 | 说明 |
|------|------|------|
| 综合知识 | choice | 75道单选题 |
| 案例分析 | case | 问答题 |
| 论文 | essay | 写作题4选1 |
