# 长时 Cron 配置审计

仅用于检查或修改本技能适用的长时 isolated Cron及其引用规则。执行规则仍以同目录 `../SKILL.md` 为准；本文件负责调度配置、静态依赖与规则传播的一致性，不自行定义研究准出。用户只要求检查时完成第1—4步并报告，不改任务、Prompt、Skill路径或工具权限。

## 1. 从调度器取得真实配置

读取调度器当前任务列表并识别目标任务，不以Prompt、记忆或旧任务ID代替。逐项记录：任务ID与名称、enabled、schedule与时区、sessionTarget、wakeMode、payload类型、timeout、lightContext、显式model、toolsAllow、delivery、failureAlert、scheduledToolPolicy、最近/下次运行及连续错误。

同类任务做字段对比，明确哪些差异是主题预算等有意差异，哪些是遗留不一致。调度器`ok/error/delivered`与业务SUCCESS/BLOCKED分开；需要评价最近业务结果时读取对应run摘要，不从顶层状态猜。

取数入口（本机实测，别再逐个试）：

- 调度配置与原生状态：`openclaw automations list --json`、`openclaw automations get <id>`；顶层 `lastRunStatus/lastDelivered` 只代表调度器。
- 最近业务结果与投递（权威入口）：`openclaw automations runs <id> --limit <n> --json` → `entries[]` 的 `status`、`completionStatus`、`durationMs`、`error`、`delivered`、`deliveryStatus`、`summary`（`summary` 就是该次 final 正文）。
- 运行身份：`openclaw audit --kind agent_run --after <ISO> --json`（含 sessionKey/sessionId/runId/status）。
- 状态库直读：**首选 Python 的 `sqlite3` 模块直连 live 库**——`sqlite3.connect('file:<绝对路径>?mode=ro', uri=True)`，实测可直读 `<state-dir>/openclaw.sqlite`（`cron_jobs`）与 `<state-dir>/lcm.db`（`messages`），无需复制大库，且能看到还在 WAL 里的刚写入事务。该拒绝只针对外部 `sqlite3` CLI（报 `external sqlite3 cannot open databases under the active OpenClaw state directory`），模块不受限。确要用 CLI：先 `cp` 到 state 目录外（state 目录路径、其相对路径乃至同名副本都可能命中；要看最新事务就连 `-wal`/`-shm` 一起复制），**复制与查询分两条命令**——实测把 `cp`/`mv` 一个 sqlite 文件与 `sqlite3` 调用写进同一条命令时整条被拒。
- 常见死路，不要再试：`openclaw message read` 在 Telegram 返回 `Unsupported Telegram action: read`；对本会话树以外的 session 调 `sessions_history` 会被当时的可见性/跨 Agent 配置拒绝（本机曾为 `tree`+关闭；配置本身见 [openclaw-session-access](../../openclaw-session-access/SKILL.md)，改它属独立授权、不在本审计内）；用 `find` 全量扫 state 目录代价极高。三者都不能当成"查不到证据"的结论。

完成标准：目标任务无遗漏，当前配置、原生运行状态和业务结果没有混称。

## 2. 递归验证 REF 与固定依赖

从payload提取全部固定REF文件，确认存在、可读且指向预期当前版本；再读取这些公共/主题Prompt，继续提取其中固定的Skill、reference、脚本和共享协议路径。模板中的`<日期>`、`{YYYY-MM-DD}`、`<run_id>`等运行期输出不是静态缺失；不带占位符的规则、Skill、reference和脚本必须逐一存在。

不能因当前交互会话能从Workshop或技能目录读到同名Skill，就假定isolated Cron能读取Prompt写死的另一条路径。Workshop管理的已应用Skill默认位于当前Agent的`<state-dir>/agents/<agentId>/agent/workshop-skills/<skill>`，与`workspace/skills`、个人Skill及其他Skill根是不同来源；先从当前Agent目录或技能清单解析真实位置，再检查Prompt的绝对路径。对每个缺失固定路径，分别报告：引用它的文件、不可用路径、通过目录清点或运行时清单核实的实际候选路径；未验证内容和版本相同前不建议静默回退、复制或建立链接。

任一必读固定依赖缺失时，配置就绪度为BLOCKED，即使Cron表达式、Gateway和上次运行均正常；不能把“REF触发词存在”写成“REF链有效”。

统一准出规则的审查须沿同一引用链检查语义，不只检查路径或文件开头：把权威标准与适配器参考、主题正文、研究/文章门控、发布外壳、末尾交付清单和汇报格式逐项对照。重点检查前文已改为目标的数量，是否又被后文“缺一不可”“TOP5/三条主线已完成”等写法恢复成硬闸。外壳只承载实际准入内容与局限，检查表记录真实完成状态；发布成功仍需对应证据。按主文件引用的共同证据标准判断，不在本审计复制第二套准出分类。

完成标准：所有静态必读路径可定位，缺失项指出第一处断点；涉及准出变更时，上下游与末尾清单也无相反要求，不能用一条顶部覆盖声明代替修正冲突原句。

## 3. 对照工具权限与执行合同

将`toolsAllow`与实际读取到的执行合同逐项对照：必需工具须获准，明确禁止的工具须从白名单排除，而不是只在Prompt里写“不要调用”。特别检查isolated任务没有`sessions_yield`；白名单含异步完成型工具（如`image_generate`）时，另须确认执行合同把该调用交给可让出回合的子会话，而不是由父级本回合直调：父级既无`sessions_yield`又发起异步任务，完成唤醒会撞上它仍活跃的回合，把原生运行打成`error`，而业务产物通常已经完成（机制与配套约束见主文件第5节）。这类缺口不要用两个看似省事的改法——给父级补`sessions_yield`会让本次运行在报告生成前收工；从白名单删掉该工具又因子会话继承父级工具策略上限，使子会话同样无法调用。普通周报以runner的announce结束时，若Prompt禁止主动发送，则任务执行白名单不保留仅用于该主动发送的`message`。runner的delivery/failureAlert不依赖任务调用`message`。

记录未知、已退役或当前schema没有的工具名；它们不能证明能力可用。不要为整齐而删除用途尚未核实的工具，修改权限须有执行合同依据并取得本次修改授权。

完成标准：硬禁用由运行时白名单落实，所有保留工具都有可说明的任务用途。

## 4. 检查时间、投递与最近失败

核对时区、同一Agent任务间隔与最大timeout，标出无缓冲相接或可能重叠的长任务；不凭一次较短耗时断言以后不会重叠。确认announce目标、channel/account解析及失败告警；多账号环境不能只凭数字目标猜账号。**审计里的 `Delivery` 是写入时刻的快照**：isolated Cron 的 final 由 runner 的 announce 在该运行结束前后投递，父级写审计时只能填 PENDING。复核真实投递状态用 `openclaw automations runs <id> --json` 的 `delivered`/`deliveryStatus`，不因审计文件仍为 PENDING 判定投递失败，也不要求父级在结束后回填。**改触发周几会连带改变报道窗口**：这类周报的主题Prompt多以触发日为窗口基准（如周五触发即"上周五→本周四"），只改小时不影响窗口，改周几必须同步复核并修正该Prompt的时间窗段，否则会静默研究错误区间。改日程前先读该主题Prompt的时间窗段，改后按第2节沿引用链复验。

同类长任务的`timeout`要横向比，并把**墙钟截断**与真实故障分开：报`timed out (last phase: …)`且`state.lastDurationMs`≈`payload.timeoutSeconds`×1000时，是预算到顶被调度器截断——错误里的phase只是被杀时的位置，不代表模型或工具卡死。用同类任务**已成功**运行的实耗给预算定尺寸（同Agent、同流程的长任务互为可比样本），记录样本区间与依据；实耗明显低于timeout却仍error的按下一段其余边界归因，不并入本条。预算是否够属配置问题，只报告结论与样本，未获授权不改任务、不重跑历史运行。本机2026-09-20观测：同流程成功任务实耗12,481—12,638秒，而报截断的任务预算7,200秒。

将最近错误归到首个真实边界：配置/引用缺失、预算不足（墙钟截断）、任务违反合同、模型或工具暂态、业务质量门控、发布验证、投递。新版Prompt尚未被下一次自然运行使用时，只能写“静态规则已具备”，不能声称历史故障已恢复。

完成标准：报告按“必须修复、建议规范化、历史/暂态观察”分级，并明确是否做了修改。

## 5. 获得修改授权后的最小修复与复检

只修已确认的断点：更新所有权威引用源，不用额外副本掩盖错误路径；按执行合同最小增删工具；保留主题有意的调度和预算差异。配置编辑前重新读取当前任务，避免覆盖并发修改；不整份替换配置。

**增删工具用 `openclaw automations edit <id> --tools "<逗号分隔清单>"`，它把 `toolsAllow` 整表替换成传入的那一串，不是增量。** 删 N 个失效工具时先 `openclaw automations get <id> --json` 取现状，构造“原清单 − 失效项”的完整字符串再提交；只把要删的名字传进去，会把白名单削成那几项（本机 7 个周报各 23 项，误传 3 个 lcm 工具名等于把任务砍到 3 个工具）。`edit` 的返回体就是改动后的任务 JSON，可直接读回项数核对；批量改逐个核对，不一次遍历改完再统一验收。实测 7 个任务 23→20 项，缺省 `--tools` 之外的参数不动，逐字段比对后除 `payload.toolsAllow` 仅 `configRevision`/`updatedAtMs` 变化；要整块去掉白名单改用无参数列表的 `--clear-tools`（改为“使用全部工具”），不当成删除一个个工具用。

修改后重新取得调度器配置，重复第1—4步；运行配置校验并确认Gateway状态。检查配置diff只含授权范围，所有固定REF链可读，硬禁用工具确已缺席，delivery/failureAlert仍解析到预期目标。使用`openclaw cron edit --tools`后必须重读`scheduledToolPolicy`：当前CLI可能把原先未显式记录的策略实体化为`trusted`等显式值；这是需要验收和报告的权限状态变化，不能只比较`toolsAllow`或宣称策略未变。改任务模型用 `openclaw cron edit <id> --model <provider/model>`（字段为 `payload.model`）。写前先快照目标任务 JSON；写后做**逐字段递归比对**而不是只看模型值，比对时排除会被运行时刷新的 `state`，其余任何非目标字段变化都要复读并报告。多个同类任务批量改时逐个核对，不用一次遍历改完再统一验收。除非用户明确要求，不为验证配置而手动运行全部长周报；下一次自然实跑前只报告静态预检通过。

委派修改后，父级先核对实际文件与交回版本/SHA，再复读第2步所列准出、外壳和末尾清单，不能把子任务“检查通过”当成语义验收。最后一次补丁后重新检查受影响文件并记录最终SHA，注明其取代先前审计值。关键词无命中、文件非空与围栏成对只证明对应静态检查，不证明没有语义冲突或已完成真实发布。

完成标准：当前配置可复读、静态依赖全通、权限与合同一致、无无关变更；最终文件版本与审计对应，规则修订与自然实跑结果分开报告。