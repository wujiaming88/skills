# 周报发布专项

适用已有研究周报/报告的发布，不适用于普通备份、提醒或无发布边界的短任务。先完整读取同技能 [SKILL.md](../SKILL.md)；通用工具、run_id、阶段状态、等待、恢复和业务终态只按其第1—3、7节，本文件只补充周报发布与announce交付规则。

## 专项依赖与参数

- 研究范围、时间窗、对象、深度目标、预算、产物清单、分类与汇报由主题Prompt指定；数据与研究准出按主文件引用的统一证据标准，不把最低覆盖、固定来源/候选数量等目标重新升级为发布硬闸。
- 研究取证按主文件第1节使用当前可用工具及已授权固定入口，正文/账本用文件工具分块。
- 固定业务助手：`/root/.openclaw/workspace/shared/scripts/weekly_ops.py`；机械助手：本技能 `scripts/reliable_cron.py`；主题Prompt明确授权的固定生图工具可继续使用。不新增wrapper或日期专用脚本。weekly_ops检查接口、状态与阶段边界只在 [weekly-ops-contract.md](weekly-ops-contract.md) 定义，启动合同、冻结输入及源预检时读取；执行时按真实help核对本期参数。
- 资料库：`/root/.openclaw/workspace/project/openclaw_daily_file`；博客：`/root/.openclaw/workspace/project/wujiaming88.github.io`。本期文件、INDEX参数和公开路径先从主题及真实站点配置核准：在run内准备候选front matter，按 [check-publication-params契约](weekly-ops-contract.md#check-publication-params) 检查并将实际config/栏目来源与解析结果登记于既有合同。不要按分类猜URL或另拼图目录；日期/basename、overlay、permalink/baseurl和适用bucket须相容，实际外壳就绪后复验。未知配置阻断对应发布边界并报告，不改站点凑通过。保留原SSH remote，不改凭据或历史。
- 仅研究、文章、发布三道验收。现有审计阶段可记研究、文章、源文件预检、构建/产物复检、双仓Git、线上正文/头图及投递；按主文件每次转阶段更新当前区，不增加另一条工具审计流水线。

## 4. 文章交接

研究内容符合统一准出标准即可冻结最终母稿及公开边界，按 `/root/.openclaw/workspace/shared/prompts/_weekly-report2article-handoff.md` 和 `/root/.openclaw/workspace/skills/report2article/SKILL.md` 执行。局部欠证经限述/归因/隔离后不延迟交接；只把最终母稿作为内容输入，不并列传入旧稿、研究分片或旧博客。编辑发现事实缺口，交研究端决定采用边界并复验受影响内容，不要求补齐所有原资料或重做全组。父级核对跨组冲突，综合判断须有依据；母稿负责人与已交接材料消费按handoff，不重复派发同职责汇总。

保留PUBLIC_CONTENT/AUDIT_METADATA/PRIVATE_INTERNAL/EVIDENCE_ONLY边界；两原清单独立冻结、真实补漏、紧凑引用、全量映射及最终正反向语义/阅读验收按report2article。编号、差异与连续阶段读取只在该Skill维护，写域/中间安全交接与父级终审按handoff；不以计数、格式或链接集合一致替代全文语义，也不生成第三套清单。新增事实、独立信息遗漏或判断漂移只修受影响部分并保留最终全文核验，不重启无关研究。

母稿与文章各自在冻结SHA前，读取 [check-inputs契约](weekly-ops-contract.md#check-inputs)，对全部待冻结普通文本一次批量检查，包括尚未进入Git的文件。检查只报告，不能证明业务PASS或替代双清单/语义验收。由唯一写入者用文件工具修报错处：Markdown双空格硬换行可用明确段落表达，先核受影响文字与渲染语义，不全局rstrip或破坏代码块；语义改动须重新对应内容验收。最终版本格式通过后再冻结SHA；保持提交前Git检查。

**冻结后才发现Git空白错误**：先按主文件确认旧写入者结束并建立修订版本。只处理报错位置；元数据原用行尾双空格换行时，可改用段落空行保留分隔，不全文件盲删空白。对照修改范围，在原审计记录旧/新SHA、具体差异及语义不变依据，并核对受影响母稿定位与映射。保留两份原清单实际提取时的输入SHA，以版本转换记录连接新版，不改旧证据冒称重新盲提取。父级复验通过后，以自己的验收记录签发新版交接标记、更新归档副本；标记的source_sha256对应新版母稿，正文未变则保留article_sha256。随后重跑受影响的输入、发布及Git检查；若现有构建证据失效，按第6节重建，不只换SHA保留失效PASS。无法证明语义不变时回到对应内容验收，不沿用本分支放行。

article.done及生产者final交接遵守主文件第2—3节。资料库保留研究母稿；博客保留完整独立信息的读者稿，非摘要版。发布外壳不能改变事实边界。

## 5. 配图

- **isolated Cron 父级不得在本回合直接调用 `image_generate`**：这类任务的 `toolsAllow` 白名单通常含 `image_generate` 却不含 `sessions_yield`，父级提交异步生图后无法让出回合声明，媒体完成唤醒会与其仍活跃的回合冲突（`ActiveTurnClaimError: Session <id> already has an active turn claim`），并把原生运行打成 `error`（`agent run aborted | OPENCLAW_DIRECT_ABORT`），而当时业务产物往往已经做完。配图由专用配图子会话提交并让出回合，父级只做核验与搬运；子会话唤醒回合为只读（无 write/exec），故文件搬运与完成标记由父级核验后自行落盘。父级取图用一次 `ls /root/.openclaw/media/tool-image-generation/`（按 filename 前缀匹配）或读子会话 final 取绝对路径，核验存在、非空、与本期内容相关后再复制。
- 每期独立生成新头图，首选内置image_generate当前配置可用模型，不显式选xAI/Grok。在选题稳定且有内容依据/授权后独立准备，不让图片或资料库准备阻塞已满足准入及资源条件的文章双线。accepted后接回同一后台任务，不重复提交；isolated父级等待仍服从主文件第3节，不能为等图片使用sessions_yield——实测让出会立即结束本次运行，父级会在报告完成前收工。不为普通单张图额外派任务。
- 首选不可用/失败/首轮明显不达标，使用已授权Stable Image Ultra固定工具；仍失败仅可用已批准且无需现场造脚本的方法生成本期新简约占位图。无可用方法时保留完整正文和资料库准备成果并汇报，只将配图相关发布边界标为未完成，不回改研究/文章结论、不重跑研究；不得复制改名旧图或伪造新图。当前校验器要求头图时，不绕过校验冒称无图博客已发布。
- 记录实际provider/model、结果、错误状态/代码（若有）和采用线路，不只写“认证异常”。文件存在/通过验收与工具完成通知分别记录，通知失败但文件有效不重复生成。保留主题Prompt的英文prompt、PNG、比例、风格及差异化要求；核验确与本期内容有关。
- 文件名以前置文章日期开头，PNG存在非空；mtime仅辅助，不能证明新图。overlay只在front matter引用一次，正文不重复站点标题/头图。
- validate-blog-post执行既有日期、引用次数、SHA256历史防复用检查。图片改变只重验相关输入，不降低事实或版本验证要求。

## 6. 固定发布顺序

以下每步独立调用，不合并成长命令；失败按主文件保留阶段证据。两个仓库不是事务，干净检查和Cron/子任务并发额度都不是共享工作树互斥锁。父级指定唯一发布者；研究和编辑只写各自run目录，不写共享仓库。发现其他发布活动则暂停冲突边界，不预建新锁服务或假称已互斥；其他可独立完成的工作继续，不把并发冲突解释成内容不合格。

1. read确认研究、文章最终全文、三材料与当前冻结版本的语义验收均已完成。用文件工具按已核准参数叠加front matter/TOC/图片路径等外壳，不改内容事实。
2. 分别检查两仓状态、预期分支、待改文件。已有他人修改或并发发布迹象时不覆盖、不reset、不stash，暂停冲突步骤。串行完成每个仓库的写入；不得并行写同文件或共享仓库。
3. 独立cp冻结母稿到资料库、已验证头图到博客；用weekly_ops.py insert-index-auto及主题Prompt原参数更新INDEX，准备博客。核对复制结果、diff与头图，不提前提交。首次真实构建前两仓分别执行必要的 `git diff --check`；对新/未跟踪文件不能靠该命令空输出放行，须由check-inputs整文件覆盖全部待提交文本，提交前再由暂存区检查覆盖实际提交范围。
4. 对实际外壳执行check-publication-params；按 [check-publication契约](weekly-ops-contract.md#check-publication) 对母稿、文章、INDEX、blog和image运行一次prebuild聚合输入预检，其同版本源稿validate已包含，不再单独重复validate-blog-post。首次使用本次真实执行接口时按真实 `--help` 核对参数一次；接口版本未变不循环help。prebuild只检查本地源，不证明语义、构建、Git、HTTP或发布。
5. 无可复用构建证据时，记录真实带时区构建开始时间，独立运行一次 `bundle exec jekyll build` 并记录exit。随后按同一check-publication契约运行一次postbuild聚合检查，验证当前产物、旧_site新鲜度、正文/图片bytes及内含的site validate，不再重复validate。只有相同冻结输入、构建配置/依赖/输出均未变且已有该版本有效真实build证据时才跳过构建；mtime或旧audit不能代证。输入改变只重验受影响边界，但若build证据失效必须重建。当前工具未能证明某项变化不影响渲染时保守重建，不由执行者删新鲜度条件、伪造构建时间或仅凭正文SHA自行启用依赖复用。
6. 提交前单独查当期脚本残留：`find <当期绝对目录> -type f \( -name '*.py' -o -name '*.sh' -o -name '*.pyc' \) -print`。空输出为无残留；发现后人工核查、不自动删除。命令异常记辅助告警，实际违规另行处置。
7. 两仓分别git status、精确git add本期文件、git diff --cached --check、git commit、git push，各为独立动作，不混成自动长链。沿用SSH remote，不修gh凭据、不改历史；某仓已正确同步则跳过该仓提交，另一仓失败只恢复另一仓。
8. 两仓分别运行 `python3 <本技能绝对目录>/scripts/reliable_cron.py check-git --repo <仓库绝对路径> --remote origin --branch main --verify-remote`。按helper真实接口确认预期分支、干净工作区、真实远端HEAD一致及无观测到的并发变化；两个只读仓库验证互不依赖时可同轮并行。不是只看push或缓存origin/main。
9. 正文与头图分别运行 `python3 <本技能绝对目录>/scripts/reliable_cron.py check-http --url <公开URL> --attempts 12 --interval 20 --request-timeout 20 --total-timeout 300`。helper接受2xx，但周报必须核对实际200及当前版本正文标题/关键内容和头图bytes。两个只读HTTP验证互不依赖时可同轮并行。图片可下载后cmp；HTML不与Markdown逐字节比较。可用web_fetch或无凭据公共curl只读检查，不造临时脚本、不绕过helper网络安全限制。耗尽后不重复push。
   - 需要整页比对时，直接运行 `diff -u <本次已验收构建HTML> <下载的线上HTML>` 并读完全部差异，不先cmp再重复定位。diff exit1表示文件不同，不等于发布失败。仅当全部差异都是已确认的样式URL构建缓存时间戳、其余HTML无差异且上述正文/头图当前版本要求已通过时，记录为部署元数据差异，不因此改源、重建或重复push；不声称HTML字节完全相同，不批量过滤数字或查询参数以凑一致。其他差异逐项核对影响，无法确认当前版本则保留未验证状态。
10. 汇总内容准出、文章、构建、双仓Git、正文/头图和投递证据，按主文件第7节、下节及主题Prompt形成真实结论。核心证据齐全立即结束，不追加gh run list、Actions/Pages API、历史会话、重复构建或非关键清理；部署诊断交另一项明确任务。

## 7. 周报终态与announce交付

- 普通周报使用既有announce：父级最终验收后返回简短、非空中文final，由runner投递；不为开始/研究完成/编辑完成向交付目标调用message，不用NO_REPLY抑制最终结论。子任务仅向父级交回。若用户明确要求中途发送，先核对它对最终announce抑制的影响；未知结果不盲重发，不承诺exactly-once。
- final生成在announce之前，预期中的投递尚未执行，应标PENDING（尚未投递）而非成功或失败；不要在该final中提前写“本条已确认送达”。后续原生runs若可用再记录delivered/not-delivered/unknown；不让父任务等待自己的结束后投递。业务可SUCCESS而Delivery=PENDING。
- 除主文件的适用证据项外，按主题Prompt报告研究/文章验收、O/F/D/J/L、实际覆盖与局限和公开链接；只在实际通过时使用成功句式。局限/通知问题单列，不回改已验证发布。
