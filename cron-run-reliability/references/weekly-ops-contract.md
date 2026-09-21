# weekly_ops.py — 周报检查接口

在启动发布合同、输入冻结、源文件预检或构建后复检时读取；执行顺序见 [周报发布专项](weekly-publication.md)，通用机械检查见 [helper契约](helper-contract.md)。本文件是check-inputs、check-publication-params、check-publication的参数、JSON和退出边界唯一来源，不定义研究或文章准出。

固定入口：`/root/.openclaw/workspace/shared/scripts/weekly_ops.py`。首次使用或接口变更后运行对应 `--help`；输入/参数失败按下列边界处理，不猜flag。三个检查均只读，不执行build、Git、HTTP、copy、commit、push、delivery或内容编辑，也不做研究/文章语义验收。

## check-inputs

`python3 /root/.openclaw/workspace/shared/scripts/weekly_ops.py check-inputs --file <绝对文本路径> [--file <绝对文本路径> ...]`

- 一次聚合全部重复--file；调用方枚举全部待冻结/待提交文本，包括新/未跟踪文件，不靠Git diff可见范围。每项须绝对路径、普通非symlink、非空有效UTF-8；从无symlink父路径安全打开，读取中inode/大小/mtime/ctime保持稳定；每文件最多64MiB；EOF恰好一个LF，不允许CRLF、裸CR或末尾空白行。整文件扫描Git默认blank-at-eol、blank-at-eof、space-before-tab及LF-only约束。工具不执行Git，不加载core.whitespace、attributes或换行过滤器；通过不替代真实提交范围的Git检查。
- stdout单JSON：`CHECK_INPUTS_PASS`（exit0）或`CHECK_INPUTS_BLOCKED`（exit1），含ok、read_only:true、semantic_review_performed:false、git_check_performed:false、whitespace_policy及limits。逐文件含path/ok/sha256/bytes/lines/issues/issue_count/issues_truncated；问题给出code/message及可取得的位置，line/column为从1起的行/字节列，byte_offset从0起。每文件展示前200项但扫描完整文件，以issue_count及issues_truncated明示未展示部分。CLI用法/缺必需参数由argparse exit2。
- BLOCKED只阻止冻结该输入。检查器不修改、rstrip或规范化文件。Markdown双空格硬换行可能与Git规则冲突；唯一写者用文件工具人工选择安全表示并核对受影响渲染、代码空格及语义，不能批量裁剪代码块/缩进/字符串。语义未变只复验受影响边界，变化则重新内容验收。版本转换按 [专项第4节](weekly-publication.md#4-文章交接)，helper不签业务PASS。

## check-publication-params

`python3 /root/.openclaw/workspace/shared/scripts/weekly_ops.py check-publication-params --blog-repo <站点源根绝对路径> --blog <根内_posts目标路径> --front-matter <候选外壳或实际post绝对路径> --expected-basename <主题规定的含日期.md文件名> --header-path </assets/images/posts/本期图片> --article-url <声明正文完整URL> --image-url <声明图片完整URL> --category <分类> [--category <分类> ...] [--bucket <显式bucket> --bucket-page <实际栏目源页>]`

- 启动合同明确后，在run目录用文件工具准备候选外壳，执行本检查；实际外壳形成后复验参数。不要求planned post/image已存在，不创建目标；读取实际`<blog-repo>/_config.yml`、候选front matter、若存在的post及适用bucket栏目源页。只读检查不执行其他程序。此入口懒加载已安装PyYAML，缺失BLOCKED、不安装、不猜测解析；旧CLI不依赖PyYAML。普通文件64MiB上限、YAML段128KiB及8192 token上限；拒重复key、anchor/alias/merge/显式tag。
- 所有路径须安全且不经symlink；blog直接在根内_posts/，basename与明确主题参数完全一致且为有效`YYYY-MM-DD-lowercase-ascii-slug.md`，不按标题改名。front matter从字节零使用LF `---`外壳；若目标post存在，候选与实际解析元数据完全相同。显式layout:single、非空title、与basename同日的date（带时间时+0800/+08:00）；categories是与重复--category有序一致的唯一列表。主题范围、旧basename、日期与分类的权威性仍由父级核对，不由helper猜主题。
- 读取真实url/baseurl/permalink/timezone/defaults；当前只支持`/:year/:month/:day/:title.html`、Asia/Shanghai及安全静态post permalink，目录URL对应index.html。未知路由、custom source/collections、会改变发布元数据的defaults、slug/category覆盖等BLOCKED。声明正文URL须与实际config及post路径推导相同，不把分类猜成URL前缀。图片URL须与config/baseurl及overlay相同。
- header.overlay_image须等于--header-path，位于`/assets/images/posts/`、以文章日期起名、扩展为png/jpg/jpeg/webp；主题若要求PNG仍须PNG。这里只验路径，不冒称已生成、图像字节或原创性通过。头图命名可与文章slug不同，保留主题差异。
- 显式bucket必须等于--bucket且给出仓库内真实公开源--bucket-page；栏目页须layout:list、list_kind:weekly、相同bucket、有效permalink且不禁用发布。拒生成/私有路径和笼统weekly_all/article页。无bucket则两个参数均省略且front matter无此字段。显式bucket优先于站点文件名推导；发现不存在/错名则修当前候选参数，不擅改历史文章或站点。栏目元数据一致不证明Liquid实际收录。
- stdout单JSON：schema_version:1、scope:local-publication-parameters；`PUBLICATION_PARAMS_OK`（exit0）/`PUBLICATION_PARAMS_BLOCKED`（exit1），用法错误exit2；含ok、read_only:true、semantic_review_performed:false、publication_verified:false、checked/failures/files/resolved/remaining_checks。files记实际文本SHA/bytes；resolved按进度记planned/existing、真实配置、basename、正文/图URL/路径、分类/bucket，失败时可不完整，不作准出。报告首个阻断，不声称一次枚举全部元数据错误。
- OK只证明本次指定参数与可读配置/外壳一致；不证明额外build config、环境、插件、Liquid、真实渲染、语义、Git、HTTP或投递。实际外壳/头图就绪后仍按原prebuild→真实build→postbuild流程。真实build开始/结束/exit必须独立记录，不由helper时间或exit替代，旧JSON不能作为新验证凭据。

## check-publication

`python3 /root/.openclaw/workspace/shared/scripts/weekly_ops.py check-publication --phase prebuild|postbuild <参数>`；phase默认postbuild。

**共用必需参数**：`--run-id --research-done --article-done --report --article --archive-repo --archive-file --index-date --blog-repo --blog --image`。除可相对各自根解析的archive-file与blog外，文件/根路径必须为绝对路径且不能经过symlink；archive-repo与blog-repo须存在、互不包含。index-date须为YYYY-MM-DD。

**交接与源文件契约**：report、article、done、INDEX、blog须为当前非空安全文件；普通文本为UTF-8且文本源满足单LF EOF。research.done与article.done须各有且只有一条顶格 `status: PASS`、`run_id: <本期run_id>`、`source_sha256: <完整report SHA256>`；article.done另须唯一顶格 `article_sha256: <完整article SHA256>`，任意BLOCKED均拒绝。archive-file必须位于archive-repo内并与冻结report完整字节一致；INDEX.md必须在index-date对应表格中有指向该archive-file的精确链接。blog必须位于blog-repo内、front matter有效，且去掉唯一外壳后正文与冻结article完整字节一致；front matter引用的博客头图须位于根内，并与绝对冻结image完整字节一致。

**文本级拒绝项**：除字节契约外，report与blog的正文还须含「第 」与「 期」的期次标记，且不得含 `第 N`、`第 X`、字面 `TODO`、字面 `待补`、字面 `\n` 及已知截断片段；blog还须含 `report` 文件名日期前缀（YYYY-MM-DD）。`待补` 是自然会写出的编辑用语（如「待补证」），一旦出现即阻断，改用证据标准用语「本次未取得」；同理 `第 N`/`第 X` 应写实际期次。blog另拒裸 URL（须写成 markdown 链接）、缩进表格行、渲染表格数与源不一致，以及内部协作标记（分组代号、产出人代号、资料库目录名等）。**精确标记清单以校验器实现为准**，改动文字前先读其对应拒绝项，不凭记忆枚举，也不为通过而删正常正文。

**prebuild**：不传 `--site --build-started-at --html-text`；聚合上述done/SHA、完整归档字节、INDEX、文章正文、front matter、头图、EOF与源版validate-blog-post。结果 `LOCAL_SOURCE_CHECKLIST_PASS`（exit0）或 `LOCAL_SOURCE_CHECKLIST_BLOCKED`（exit1）。本入口未替代check-inputs的整文件空白扫描，也未包含check-publication-params的配置/栏目检查，分别在各自边界执行，不误称已聚合。

**postbuild**：在共用参数上必须再传 `--site <当前构建根绝对路径> --build-started-at <带时区ISO-8601真实构建开始时间> --html-text <探针>`；html-text可重复，每项必须是非空且来自本期冻结article的正文纯文本，并须出现在当前构建HTML可见文本中。site须为当前绝对构建根；HTML路径按本期post/permalink推导，构建头图与冻结image完整字节一致，HTML不得早于真实build开始或当前发布输入，并执行site版validate-blog-post。不得用旧audit、保存的helper输出或单独mtime代替本次真实build exit0与当前输入绑定。

本接口未启用新的旧build复用：既有phase、完整字节/done SHA/当前HTML图/mtime freshness条件保持。仅母稿格式或mtime变化也不得绕过原门控；文章单项SHA、audit PASS、旧helper JSON或手工回拨时间不是依赖证明。未有完整、保守、经反例验证的渲染依赖与真实执行/输出绑定时按专项保守重建，不猜测非渲染文件例外。

postbuild结果为 `LOCAL_CHECKLIST_PASS`（exit0）或 `LOCAL_CHECKLIST_BLOCKED`（exit1）。缺少共用必需参数、postbuild三项参数或其他CLI用法错误由argparse exit2。两阶段JSON均含 `publication_verified:false`；通过仍不替代研究/文章语义、真实build exit0、双仓真实remote、线上正文/图片当前版本或announce。
