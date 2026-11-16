# 测试与 Review

命令示例基于入口所列快照。先核对目标 `package.json`、`vitest.config.ts`、Nx targets 与 CI，尤其是参数转发与排除项。不要为旧 fork 安装上游新测试框架。

## 环境和验证层次

当前上游使用 pnpm + Nx，root `packageManager`/`devEngines.runtime` 固定工具链。`pnpm install` 后用 `pnpm run doctor` 检查环境。只为本次验证准备需要的浏览器、Docker 或 Agent CLI。

| 修改范围 | 验证对象 | 该快照的入口 |
| --- | --- | --- |
| service、状态转换、工具函数 | 输入/输出、错误、取消、事件顺序 | App Vitest `node` 或所属包测试 |
| Wire/API | contract 校验、controller 注册、client 调用与事件/状态更新 | 同域单测，加跨边界集成验证 |
| 数据库 | 真实 SQLite、旧数据升级、迁移后读写 | `main-db`、`db:fixtures`、`test:migrations` |
| UI 交互/布局 | 用户动作、焦点、真实 CSS/layout、卸载重挂 | App `browser`、UI tests、Storybook |
| Chat 流式/虚拟列表 | 测量、追加、重挂、滚动与长历史性能 | chat-ui tests；相关时 `test:perf` / `test:bench` |
| PTY/SSH/远程 | 临时仓库、进程生命周期、断连恢复、Host 正确性 | 对应 core/app tests；相关时远程 WSS 集成 |
| 打包/升级 | 打包脚本、文件资源、native ABI、真实产物启动 | `scripts` 项目与 packaged checks |

常用命令及工作目录：

```bash
# 仓库根：按包执行，参数传给 Vitest
pnpm --filter @emdash/emdash-desktop test -- --project node <test-file>
pnpm --filter @emdash/emdash-desktop test -- --project browser <test-file>
pnpm --filter @emdash/core test

# 仓库根：只读检查；适用于 Review，避免格式化重写被审查代码
pnpm run format:check
pnpm run lint
pnpm run typecheck
pnpm run test

# App 目录：仅涉及 schema/migration 时
pnpm run db:fixtures
pnpm run test:migrations
```

`<test-file>` 替换为真实测试路径，不原样执行。迭代时运行相关测试；交付/PR 前执行项目要求的 gate。当前 `pnpm run check` 内部先运行 **会写文件的 `format`**，再 lint/typecheck/test；Review 默认用上面的只读形式。不要把全仓格式化产生的无关差异混进提交。

### 不能混淆的结果

- 当前 CI/`EMDASH_TEST_SKIP_BROWSER` 会排除 browser projects；CI 绿灯不代表 UI 测试已跑。UI 变更在本地明确执行 browser 项目并确认实际测试数，不能用跳过标记制造成功。
- `better-sqlite3` 的 system-Node 测试构建与 Electron ABI 构建是两份；当前 node tests 通过 `tooling/node-deps` alias 使用隔离构建。ABI 故障按 doctor/项目脚本修复，不反复互相覆盖。
- Fixture 生成不是迁移验收；mock RPC 不是 SSH 验收；网页组件测试不是完整 Electron E2E；bundle 构建成功不是安装包启动成功。
- 远程 WSS 集成使用当前 `apps/workspace-server` Docker stack 与 app `test:workspace-server-remote`。真实机器验证只使用任务授权的机器/环境，并报告本地、容器和真实远程的覆盖差别。
- 测试应使用隔离临时 repo/worktree/数据库与项目提供的 home 隔离机制，不访问用户真实 Git 配置、会话或工作数据库。

## Bug 与新功能

Bug 先把具体触发步骤变成失败测试，保留修复前后结果。新功能测试用户可观察行为，至少包括主路径与本次改动引入的重要失败/边界路径。不要只测试实现细节或大段快照来替代行为断言。

异步行为优先验证任务切换、晚到结果、重复请求、取消和重挂是否与实际生命周期相符；仅选择本次修改涉及的情况。测试未执行、无匹配测试、环境启动失败与断言失败分开报告。

## Review 模式

1. 明确审查范围：未提交 diff、某次提交或 PR 与指定 base；不擅自选另一基线。读完整相关调用链、现有测试和必要配置。
2. 按真实影响检查：跨平台/跨进程边界、Host 与状态 owner、事件竞态、路径/命令安全、数据兼容、UI kit/主题/键盘/生命周期、构建资源与更新行为。
3. 每项发现写明严重度、文件/行、触发条件、用户影响和最小修复方向；区分已经复现的缺陷与尚待验证的风险。不要把个人样式偏好当作阻断缺陷。
4. 先报告缺陷，再说明测试覆盖与缺口。没有可证实问题就明确说明未发现可操作缺陷，同时保留实际未测范围；Review 请求不自动授权重构或修复。

来源：[Developer flows](https://github.com/generalaction/emdash/blob/main/agents/workflows/flows.md)、[Vitest config](https://github.com/generalaction/emdash/blob/main/apps/emdash-desktop/vitest.config.ts)、[CI](https://github.com/generalaction/emdash/blob/main/.github/workflows/code-consistency-check.yml)、[PR template](https://github.com/generalaction/emdash/blob/main/.github/PULL_REQUEST_TEMPLATE.md)。
