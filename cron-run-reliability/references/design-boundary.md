# 可靠性规范责任索引

仅在维护、合并或检查规则归属时读取，不是额外执行流程。保留本路径供既有引用使用；通用可靠性与按需周报专项仍是同一个Skill，不新增控制器。

| 需要维护的内容 | 唯一权威位置 |
| --- | --- |
| 适用门、禁止新增的系统/配置变更、工具边界、run身份、阶段/标记、等待、恢复、业务终态 | [SKILL.md](../SKILL.md) |
| 调度配置、递归REF、工具权限、投递静态预检及准出规则传播 | [config-audit.md](config-audit.md)；不另定准出或用静态通过代替自然实跑 |
| reliable_cron.py文件/Git/HTTP机械接口、安全、JSON/退出码及回归维护约束 | [helper-contract.md](helper-contract.md)；检查不是语义验收、锁或未来状态保证 |
| 异常症状到既有规则的定位 | [common-failure-playbook.md](common-failure-playbook.md)；不复制恢复流程 |
| 固定搜索适配器及其权限边界 | [research-contract.md](research-contract.md) |
| 周报交接、配图、构建/双仓/线上当前版本顺序与announce交付 | [weekly-publication.md](weekly-publication.md)；普通长任务不加载 |
| 周报check-inputs/check-publication参数、源/构建契约及JSON/退出码 | [weekly-ops-contract.md](weekly-ops-contract.md) |
| 研究逐主张证据与准出 | [industry-research-evidence](../../industry-research-evidence/SKILL.md)；主题Prompt保留范围与深度目标 |
| 主题Prompt的定位、覆盖范围与产出字段变更 | [weekly-report-rule-change](../../weekly-report-rule-change/SKILL.md)；只增强不新增任务，研究范围与深度目标仍归主题Prompt |
| 文章语义保真 | weekly-publication第4节引用的report2article及既有交接协议 |

不在本索引再抄写执行规则。脚本、测试路径及生产断言保护等维护要求已归入helper-contract的“回归测试同步”；文档整理不代表生产实跑通过。

**不在本集合**：僵死后台任务的注册表清理（`openclaw tasks audit` / `cancel` / `maintenance`、留证后删子会话）归 [openclaw-task-cleanup](../../openclaw-task-cleanup/SKILL.md)；本集合只负责 run 内的等待与恢复，不在此处另立一份。
