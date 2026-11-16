# 架构与开发导航

以下路径基于入口所列上游快照。先查目标分支是否存在；`src/...`、`scripts/...`、`drizzle/...` 默认为 `apps/emdash-desktop/` 下路径，`packages/...`、`agents/...` 是仓库根路径。

## 所有权与调用链

```text
React feature UI → feature api/domain client → seeded Wire connection
  → preload MessagePort → desktop gateway → feature node/controller → service/runtime
  → SQLite / Git / PTY / ACP / workspace host
返回：Result、live model、event stream、live job
```

| 关注点 | 当前源码入口 | 修改原则 |
| --- | --- | --- |
| Electron 启动与进程桥 | `src/entry/main.ts`、`src/entry/preload.ts`、`src/main/bootstrap/` | main 负责宿主与启动；preload 保持窄接口 |
| 垂直功能切片 | `src/core/features/<feature>/{api,node,browser,contributions}/` | API 放契约/类型/客户端，Node 放实现，browser 放界面 |
| 通信装配 | `src/core/manifests/shared/desktop-wire-contract.ts`、`src/core/manifests/node/controllers.ts`、`src/main/gateway/desktop-wire.ts` | 新契约和 controller 必须接入实际 gateway，不能只写孤立实现 |
| 可移植运行时 | `packages/core/src/{runtimes,services,primitives}/` | 沿用 API/platform surface、依赖方向和生命周期 Scope |
| Provider | `packages/plugins/src/agents/impl/`、`packages/plugins/src/agents/registry.ts` | Provider 差异放插件边界，不污染通用会话协议 |
| 远程主机 | `apps/workspace-server/`、`src/core/services/ssh/` | 文件、Git、进程在拥有资源的 Host 执行 |
| 数据库 | `src/core/services/app-db/node/`、`src/main/db/`、`drizzle/` | 数据库由启动阶段构造，服务显式接收依赖 |

跨切片从其 `api/` 或贡献注册机制访问；browser 不得导入 `node/`。共享包通过 `package.json` 的 `exports` 使用，不新增绕过边界的内部路径别名。旧版 checkout 沿用其现有 typed IPC/RPC，不为一个小功能引入完整 Wire 迁移。

### Wire 与生命周期

- 过程调用、通知、共享状态、可取消工作分别沿用 `procedure`、`eventStream`、live model、live job。订阅确认必须代表资源就绪时，核对 `resourcedStream`，不要用可能丢失的一次性 ready 事件。
- Renderer bootstrap 只种入一次 Wire connection；功能从 owning slice 的 domain client 获取服务，不自行创建连接。
- 预期失败使用现有 `Result<T, E>`；controller 委托 service/operation。协议错误应能映射到明确的 UI 状态，不能只记录日志后返回假成功。
- 服务由 composition root 构造，依赖显式注入。订阅、worker、watcher、终端与连接的 dispose/cancel 属于实际 owner；测试视图反复挂载与异步结果晚到。

## 状态与远程语义

- Desktop SQLite 拥有 project/task/conversation 等桌面实体与绑定；Host 拥有实际 repository/worktree/branch/process。桌面镜像行不是远程资源存在或删除成功的证明。
- 当前删除流程使用持久 tombstone 与 reconcile；不要另造命令队列，或将 RPC ack 当作 UI 最终真相。改动前读 `agents/architecture/state-ownership.md` 的对应状态机。
- Task/Project store 使用当前 selectors 和 view hooks，例如 `getTaskStore`、`asProvisioned`、`asAvailableProject`；处理空值，不用 `asProvisioned(...)!`。ready guard 判断 `kind !== 'ready'`，避免漏掉未来状态。
- 项目配置按 owner 保存原始层，不把“合成后的有效配置”整包回写。当前 `projectConfig` 暴露 `{ value, from }`；适用字段的优先级为 personal → workspace `.emdash.json` → host default → built-in，数组替换而非合并。逐字段核对 `agents/architecture/settings.md`。
- SSH 断连、Host 不可达、取消、恢复与重试是不同结果；本地 CLI/环境变量/凭据存在不代表远程具备。路径与命令构造走已有 Host-aware 和 escaping helpers。

## Agent / PTY / ACP

- TUI 路径走 PTY；结构化聊天走 ACP。改动发送、停止、恢复、权限请求或流式响应时先定位具体通道，不能把两者的状态或事件混用。
- Provider 新增/调整同时核对能力声明、可执行文件发现、参数与环境、ACP 适配、状态投影、图标和 UI 能力展示。仅改下拉框或 logo 不等于接入成功。
- ACP 会话状态机在 `packages/core/src/runtimes/acp/`；Provider 专属消息转换在插件边界。保留会话身份、事件顺序、取消与错误语义。
- PTY 环境经 `packages/core/src/services/pty/api/terminal-env.ts` 构造。GUI 启动、login shell 与终端启动的 PATH 可能不同；不能在 renderer 直接 spawn 或拼接 shell 命令。
- 后台子进程沿用 launch helpers；Windows background spawn 保留 `windowsHide: true`。用户主动打开编辑器/外部终端等可见应用按现有例外处理。

## 数据兼容

模式改动先定位所属 schema，使用当前 `db:generate <schema>`；不要手写修改编号迁移或 meta。结构化 JSON 演进复用 `defineVersionedSchema` 与对应列适配，覆盖旧数据、逐级升级和 future-version 行为。用隔离数据库测试，禁止拿用户实际数据库做 reset 或迁移试验。

## 按需继续读的上游资料

以目标 checkout 文件为准；缺文件时用下方官方目录找相同主题。

- [架构总览](https://github.com/generalaction/emdash/blob/main/agents/architecture/overview.md)、`agents/architecture/core-modules.md`、`state-ownership.md`、`path-system.md`、`settings.md`。
- [Wire 约定](https://github.com/generalaction/emdash/blob/main/agents/conventions/ipc.md)、`main-patterns.md`、`renderer-patterns.md`。
- [Provider](https://github.com/generalaction/emdash/blob/main/agents/integrations/providers.md)、`agents/architecture/acp-runtime.md`。
- [远程开发](https://github.com/generalaction/emdash/blob/main/agents/workflows/remote-development.md)、`agents/architecture/workspace-server.md`；版本协商/协议变更同时查 server 与 client。
- `agents/risky-areas/{database,pty,ssh}.md`、`agents/conventions/versioned-schemas.md`。
