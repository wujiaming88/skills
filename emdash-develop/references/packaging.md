# 桌面打包与交付

面向源码 fork 的本地安装包构建。构建、打包、签名/公证、启动验收、安装替换、公开发布分别报告；用户已经授权的步骤继续执行，不重复索要授权。

## 开始前核对

- 目标 commit/工作区改动、版本、平台、CPU 架构和渠道。用户未限定且仅要本机体验时，可说明按当前机器平台/架构构建；分发给其他用户时需确定目标。
- 阅读目标分支的 app `package.json`、`electron.vite.config.ts`、`electron-builder*.config.*`、`scripts/release/` 与 `agents/risky-areas/updater.md`。不要凭旧版本的 `dist/`、`release/` 路径推断产物。
- 核对 root workspace build 顺序与原生依赖准备；当前 app `build` 是 electron-vite，不能单靠它保证所有共享包最新。先走 root `pnpm run build`，或该版本已有的等效依赖构建入口。
- 本地 fork 要核查 product/app identity、user-data、更新 feed、stable/canary 是否与已安装版本共享。发现相互覆盖风险时提出最小隔离方案；不要为了打包随意改官方 appId、关闭安全策略或接管上游发布渠道。

## 本地打包命令

以下是入口所列快照的用法。先核实脚本存在及参数转发：

```bash
# 仓库根：先构建依赖与应用
pnpm run build

# apps/emdash-desktop：三选一，按本次目标平台执行
pnpm exec electron-builder --mac --publish never --config electron-builder.config.ts
pnpm run package:linux
pnpm run package:win
```

当前 `package:linux`/`package:win` 内置 `--publish never`，`package`/`package:mac` 没有。上面的 mac 命令在 root build 后直接使用同一 builder 配置并禁止发布；若目标分支的打包脚本还有必要的准备步骤，先保留那些步骤，再明确给实际 electron-builder 调用传入 `--publish never`。

目标架构来自真实配置或显式参数，不把本机架构与默认 target 等同。当前 mac 默认 arm64、Windows/Linux 默认 x64；构建其他架构先检查工具链、原生模块和平台支持。不承诺在单一主机上完成全部平台签名与验收。

## 产物验证

1. 从本次日志和 output 配置定位新产物，排除旧包混淆；记录版本、来源、文件大小和 SHA-256。
2. 检查实际包内容：main/preload/renderer、迁移文件、worker/adapter、语言服务、静态资源，以及所用原生模块的架构与 ASAR unpack 位置。
3. `better-sqlite3`、`node-pty`、文件 watcher 等必须满足目标 Electron ABI/N-API 与架构；使用本版本脚本，不对所有 native 模块盲目统一 rebuild。当前本地 `rebuild` 只重建 better-sqlite3。
4. 修改 SSH 或依赖打包时，核对 `ssh2` external 与其相对路径 helper；修改语言服务时核对 TypeScript `.d.ts` 等运行时资源。按需执行 app 目录下的 packaged regression：

```bash
EMDASH_TEST_PACKAGED_SSH=1 pnpm exec vitest run --project scripts scripts/release/lib/packaged-ssh.test.ts
EMDASH_TEST_PACKAGED_LSP=1 pnpm exec vitest run --project scripts scripts/release/lib/packaged-language-servers.test.ts
```

这些检查可能构建精简测试包；通过并不代表最终完整安装包已启动。若目标版本有 verifier，使用它检查最终包，并阅读参数帮助。

5. 用该版本支持的隔离 user-data/数据库入口启动最终包，避免触碰现有用户数据；若没有隔离入口，先确定合适的测试配置。至少走一条改动相关桌面流程，检查启动和功能日志中的错误。
6. 记录签名、公证、staple/Gatekeeper 或对应平台签名状态。未配置签名身份时交付可用的本地开发包并明确未签名/未公证；不能宣称满足正式分发要求。不要建议关闭系统级安全机制来掩盖构建问题。

## 更新与发布改动

只有涉及更新或获得发布授权时展开此节。

- 以当前更新服务、builder 配置和 release workflow 为准，检查 stable/canary identity、版本选择、目标架构集合及 manifest/哈希一致性。文档可能存在渠道信息冲突，必须查实际代码。
- 下载由后台服务持有，UI pending 不等于完整下载生命周期；检查视图卸载、重复下载请求、状态快照与进度事件竞态。
- 发布走现有 release pipeline，不单独上传半套架构或提前覆盖 live manifest。当前 release 实现包含最终文件验证与统一 finalize；不要绕过签名后哈希重算和既有恢复机制。
- 本地 fork 的打包成功不意味着可向官方 GitHub/R2 发布；按用户指定目的地与已有授权处理。

交付示例：`已生成 <绝对路径>；macOS arm64；来源 <commit + 工作区说明>；SHA-256 <hash>；签名/公证 <状态>；最终包启动与功能验证 <结果>；未覆盖 <范围>。`

来源：[打包流程](https://github.com/generalaction/emdash/blob/main/agents/workflows/flows.md)、[Builder config](https://github.com/generalaction/emdash/blob/main/apps/emdash-desktop/electron-builder.config.ts)、[Updater 风险说明](https://github.com/generalaction/emdash/blob/main/agents/risky-areas/updater.md)、[Release scripts](https://github.com/generalaction/emdash/tree/main/apps/emdash-desktop/scripts/release)。
