# reliable_cron.py — 固定工具契约

此处定义reliable_cron.py机械接口、安全和输出边界；运行身份、等待决策、恢复、终态以 [SKILL.md](../SKILL.md) 为唯一来源。以下<技能绝对目录>均解析为本技能SKILL.md所在目录，任务目录必须是明确绝对路径。helper不创建调度、不生成/编辑业务内容、不执行构建、Git写入、HTTP发布或通知。仅周报输入冻结和构建预检需要另读 [weekly_ops接口](weekly-ops-contract.md)。

## wait

`python3 <技能绝对目录>/scripts/reliable_cron.py wait --file /absolute/run/completed.marker --timeout 600 --interval 30 --min-bytes 1`

- 多文件重复--file；每条命令--min-bytes仅一次。仅等待阶段完成标记，正文/账本另外check-files。
- 每个路径须存在、为普通非符号链接文件并达到阈值。
- 兼容--glob；每个匹配须通过，空匹配失败。glob不能证明预期数量，精确清单用重复--file。
- 超时输出单行JSON `status: "WAIT_TIMEOUT"`、`ok: false`、exit0；它是检查点，后续只按主文件第3节。

## check-files

`python3 <技能绝对目录>/scripts/reliable_cron.py check-files --file /absolute/run/file.data --min-bytes 1`

相同阈值可重复--file，不同阈值分开调用。缺失、空、非普通文件、symlink失败。结果只描述安全打开期间inode元数据，不证明语义、来源、run身份、glob基数或未来稳定；父级仍核验清单、版本、status和业务门控。

## check-git

`python3 <技能绝对目录>/scripts/reliable_cron.py check-git --repo /absolute/repository --remote origin --branch main --verify-remote --command-timeout 30`

- 必须检出指定分支；工作区干净，无merge/rebase/cherry-pick/revert/bisect；HEAD等于远端分支。
- --verify-remote使用真实git ls-remote，不信缓存tracking ref；前后快照一致，观测到并发变化保守失败。它不是锁，也不保证检查后不变。
- 每个Git命令用进程组；超时/中断由helper内部TERM再KILL并输出脱敏证据，不授权父级kill正常wait。

## check-http

`python3 <技能绝对目录>/scripts/reliable_cron.py check-http --url https://example.com/published-resource --attempts 5 --interval 10 --request-timeout 20 --total-timeout 120`

- 仅无凭据公网HTTP(S)。任一DNS答案非全球可路由即失败；每次跳转和最终URL重验，固定已验证DNS地址防rebind。
- 输出省略查询参数/fragment，异常标准化脱敏。每请求及总时限包括有界worker生命周期；清理宽限可轻微超时并保守失败。
- 机械通过接受2xx，不验证业务版本；任务要求200或当前正文/图片时另验。周报固定重试参数只在weekly-publication.md定义。

## reliable_cron.py输出与退出码

每次stdout恰好一个JSON对象，按JSON status/ok解释，不解析stderr或匹配散文。成功exit0/ok:true；WAIT_TIMEOUT exit0/ok:false；无效参数、机械未过或内部失败exit2/ok:false；SIGINT/SIGTERM清理活跃Git/HTTP worker，status:INTERRUPTED，exit130。机械验证不能覆盖业务语义，网络失败不得关闭安全限制。

## 回归测试同步

验证“目标在等待开始后才出现”时，先由测试启动helper，并用测试启动器的明确ready标记确认helper已进入首次失败检查后的sleep，再创建目标文件；保留`checks >= 2`等原断言。禁止先启动固定延时写入再启动CLI，避免解释器/进程抖动导致首次检查前文件已存在而把合法`DONE/checks=1`误报生产失败。修改后先跑完整套件，再有限重复目标方法；一次偶然全绿不能证明竞态消失。ready屏障仅用于测试fixture，不得放宽生产断言或改变helper行为。

现有 `scripts/reliable_cron.py`、`scripts/test_reliable_cron.py`、`scripts/test_reliable_cron_regressions.py` 的接口、安全边界与路径保持不变；其变更须另行开发和回归验证。Skill和参考内容修改按当前Workshop维护政策执行；文档或测试通过不表示生产实跑已经通过。
