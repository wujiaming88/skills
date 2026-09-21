# 固定研究工具入口

这里只澄清已有工具用法，不改变研究来源标准、不扩大运行时权限。主题已要求Serper/Tavily/Exa搜索时，使用以下固定适配器；公开GitHub结构化读取使用以下认证GET入口。其他入口须有明确授权。搜索只发现线索，拟采用主张须有充分读取的来源支持。

## 1. 核对入口与搜索结果

1. 使用适配器前读取`/root/.openclaw/skills/web-search-plus/SKILL.md`及真实help。固定入口为`/root/.openclaw/skills/web-search-plus/scripts/search.py`，文档声明版本2.8.1；已核SHA256为`bd362b871876d6ea5dbffe5e2fff5dbb39dc4089c2d96e9751c45e4ca6e121c2`。脚本变化后先经维护验证，不在周报现场改工具。
2. 每次逻辑运行首次搜索核对实际返回provider，在现有账本记录query、时间、cached、结果/错误。内置web_search使用维护时验证的配置，不在Cron现场改路由。指定`-p`并不保证无跨源回退；核对实际provider及回退记录后再归因。明确额度耗尽的入口本次运行内不重复请求，未耗尽的已授权入口可继续。
3. 搜索使用冻结窗口，并另核原文日期；结果可能含窗口外文章，自动answer和snippet不作为已读来源。0结果不等于无动态，改精确标题、官方域或直接来源定位后再记录局限。

查询示例：

```sh
python3 /root/.openclaw/skills/web-search-plus/scripts/search.py -p serper -q '<本期公开查询>' --max-results 5 --no-cache
```

provider按主题允许入口选择实际支持的tavily或exa；参数分别引用，不以字符串拼接Shell。只读指不作对外业务写入，可保留工具已有本地缓存或本run证据，不输出密钥或提交私密查询。

固定脚本的限制：429/503已有内部有界重试，但当前未读取Retry-After；缓存键未包含全部raw_content/depth/域过滤参数。正文、深度或域过滤查询使用`--no-cache`，不把外层退避规则称为已修复内部实现；返回限流后不在外层追加重试，保留错误并转已授权备用或记缺口。401/403/审批拒绝不修凭据、不绕过。一次性测试包装不属于周报固定入口，不在Cron中复制或发明包装。

`x_search`是否存在以当前schema为准，缺失不等于所有搜索不可用；本合同不新增xAI适配器授权，不许改配置、安装或运行下载代码。

## 2. 取得并复用正文

1. 按`web_fetch → 官方导航/已发现的Markdown入口 → 固定Tavily raw_content → 必要时browser`补取；某层已充分取得即停止，不为走完链条重复请求。**文档站的Markdown入口要主动取，不等HTML失败后再试**：在页面URL后加`.md`取孪生页，并先读站点`llms.txt`索引定位具体页面。实测这类文档站的HTML版会因页面过大只回传不完整响应（`Response body incomplete`），提取后常只剩导航，spill续读也补不回正文表格，而同一页的`.md`版一次即可取全；因此HTML层取得内容过短不证明该页无内容或来源不存在，改取Markdown孪生页而不是记成缺口。动态网页可直接使用browser，先读其技能并检查status/tabs；默认text选取不适用时选择实际存在的正文元素，不把未命中selector当浏览器失效。登录、验证码和权限拦截交由人工，不绕过。
2. Tavily正文读取使用以下已核参数，并确认目标URL匹配且`results[].raw_content`非空；provider回退后缺少raw_content不算恢复。`cached=false`只证明本地缓存未命中，不能证明供应商无缓存。

```sh
python3 /root/.openclaw/skills/web-search-plus/scripts/search.py -p tavily -q '<目标文章URL>' --depth advanced --include-domains '<目标域名>' --raw-content -n 1 --no-cache
```

3. 将取得文本保留在本期授权目录，用read续读截断内容；核对标题、日期、首段、末段与中间结构，只有导航、标题、登录页或未读附件不算全文。没有结论标题的文章核对其实际末段，不机械套格式。raw_content是提取文本，不宣称与实时DOM/图片逐字等价；answer/snippet不用于补齐缺文。
4. 在现有账本按来源URL登记唯一取证主责、取得时间、正文路径/SHA、版本/日期、完整性和缺口。其他研究线只读复用已交接且足以支持同一主张的正文和仓库元数据，不覆盖他线文件、不建第二套总账。父级验收新取得的同源证据后更新相关缺口，保留失败历史，消除同一版本同时标已取得/未取得的冲突。版本、窗口或所需段落不同才补取；此为协作协议，不是自动缓存服务。

## 3. 公开GitHub认证GET

1. 读取GitHub技能，核对当前agent有效身份；专属configured=false不等于有效认证不可用。使用现有认证验证实际调用环境：

```sh
gh api --hostname github.com --method GET user --jq '{login}'
```

2. 验证成功后，公开仓库结构化取证优先用现有`gh api --hostname github.com --method GET`，限`rate_limit`与任务涉及的公开`repos/<owner>/<repo>`、`releases`、`commits`，按真实help选择字段和分页。需要状态/额度证据时使用`--include`；用户资料仅保留login。示例：

```sh
gh api --hostname github.com --method GET rate_limit --include --jq '{rate}'
gh api --hostname github.com --method GET repos/truefoundry/trueforge --include --jq '{full_name,html_url,stargazers_count,forks_count}'
gh api --hostname github.com --method GET 'repos/truefoundry/trueforge/releases?per_page=1&page=1' --include --jq 'map({tag_name,html_url,published_at,created_at,prerelease})'
```

3. 每仓库元数据由主责查询并按第2节复用；记录时间、响应字段、分页范围与额度头。单页不是全量，`--jq`输出是字段投影；额度body与响应头冲突时并列保留，不猜唯一余额。stars是取得时快照，周增速必须有对应跨期快照；release updated不冒充published_at。
4. 认证不可用或限流时记录缺口，必要时读取公开HTML/Atom；不在Cron登录、替换凭据、扩scope或导出token，不以匿名API反复重试认证查询。只读公开资料的许可不扩展为私有仓库访问或写入。

## 准出标准不由适配器改变

全部已接入周报的来源与逐主张准出统一使用主文件引用的共同证据技能；主题保留范围与深度目标，适配器不另定双源硬闸或把共同标准限于某一刊。固定适配器成功不证明正文已读，获取失败不等于静默。官方DOC等特殊附件如当前已批准工具无法安全完整提取，记录缺口，依共同标准限述或排除受影响主张；工具能力问题另行维护，不新授宏、LibreOffice wrapper或catdoc调用权限。
