# UI、样式与交互

先读取目标 checkout 的 `agents/conventions/ui-kit.md`、`ui-styling.md`、`renderer-patterns.md`，找相邻页面和组件 Storybook。下面的组件名称和注册机制只适用于入口所列快照或具有相同实现的分支。

## 设计系统的使用边界

- 桌面壳为 React；按钮、表单、弹层、菜单、提示、Toast、Tab 等来自 `@emdash/ui` 的实际 export subpath，例如 `@emdash/ui/react/primitives`、`@emdash/ui/react/patterns`。不要假定包根路径导出所有组件。
- Feature-local Tailwind 可用于布局、间距、排版的一次性组合；通用可复用的带样式组件放 `packages/ui`，使用 vanilla-extract recipes 和 Base UI 模式。不要引入第二套 shadcn/cva kit，也不重建上游已删除的旧 kit。
- 应用专属组件留在 owning feature 的 `browser/`，从 UI kit 组合。App 侧 class 合并使用 `src/core/primitives/styling/browser/cn.ts`；UI 包内部按其 VE 约定处理。
- 颜色、字号、圆角、间距、密度与状态反馈从现有 tokens/recipes 派生。`@emdash/theme` 生成 `--em-*`，主题 class 为 `emlight`/`emdark`；app chrome 在 `src/renderer/index.css` 映射。不要散落硬编码品牌色或为一页设置全局覆盖。
- 改主题源定义后运行当前 codegen，检查生成 diff；不直接补丁 `packages/theme/src/__generated__/`。同时检查系统主题切换、显式主题和密度设置。

## 样式与组件选择

| 需求 | 优先沿用 |
| --- | --- |
| 少量互斥值 | `Select` |
| 可搜索实体/大量候选 | `Combobox` / `ComboboxPopover` |
| 命令/动作 | `DropdownMenu`；右键用 `ContextMenu` |
| 任意交互面板 | `Popover` |
| 主动作和备选动作 | `SplitButton` |
| 编辑器提及/斜杠补全 | `ComboboxPopup` |
| 页面级记录列表 | `CollectionView`；树、侧栏、文件 diff、网格不强套此模式 |
| 设置页 | `PageLayout.Header`、`SettingsSection`、`SettingsRow`、`SelectableCard` |

Popup 宽度根据内容选择 trigger/content/content-at-least-trigger，不靠定位偏移碰巧撑开。密度沿用组件支持的 variant，不自行发明每页一套行高。

在 `packages/ui` 中，每个 CSS 属性只有一个 owner。用组件自身的 variant/`data-*` 表达状态；复用 menu/popup/input recipes；不要用跨组件 `globalStyle`、高 specificity 或 `!important` 穿透内部样式。遵守 `reset < tokens < base < recipes < utilities`，注意 unlayered 样式会压过所有 layer。

新增或扩展 UI kit 组件同时补齐 Storybook variants/states 与适合的行为测试。

## 页面与交互接入

- 模态框、视图、任务 Tab、设置页和命令通过 feature contributions 与 manifest/catalog 注册，找同类注册示例。不要在 app shell 塞第二套路由或全局弹窗状态。
- 模态框通过 typed open API 获得完成/取消结果，沿用焦点管理、Esc、outside press、顶层 modal stack 与 `useCloseGuard`。只有正在进行的关键操作需要阻止被动关闭。
- 命令使用 `defineCommand`、command catalog 与 view scopes；快捷键从当前设置与 command 定义派生，不把官网默认键位写死在 UI 或另加全局 keydown。核对 macOS Cmd、Windows/Linux Ctrl、用户解绑后的提示消失及编辑器/PTY 输入冲突。
- 列表保留选择、范围选择、空态、加载与失败反馈。Query-backed `CollectionView` 使用 `useQueryListSource`；有旧行时 refetch 不清空已有内容。行点击用于打开；动作菜单与多选语义沿用现有模式。
- 设置表单保存原始 override，明确 inherited/effective 值；提供 pending、error 和防重复提交，失败时保留用户输入。
- Workbench chrome 状态经已有 command store 修改；面板显隐由 store 驱动，尺寸交给 resizable panels 的 memento storage。不要另建 localStorage/MobX 像素尺寸副本或直接调 panel resize/collapse 绕过语义命令。
- 保持 titlebar 的拖动区域与可交互控件分离；需要拖动区时先用现有 Header/布局组件的 prop。

## 聊天和终端不是普通页面

`packages/chat-ui/ARCHITECTURE.md` 和其 `package.json` 是事实入口。该快照的聊天 transcript 内核使用 **SolidJS + 预计算布局 + 虚拟化**，React 宿主与聊天内核不是同一渲染层。

- `ChatContext`、会话级 `ChatState`、挂载级 `ChatView` 的生命周期不同；卸载 view 不能清空 transcript。
- 改字体、宽度、Markdown 或消息组件时，同步核对测量与投影；单改 CSS 可能使预计算高度失真。验证长消息、代码块、流式追加、滚动锚点与会话切换。
- 保留现有虚拟化与解析缓存，不能为视觉修补改为全量渲染长历史。
- xterm/PTY 历史来自后台 ring buffer，前端不新增第二套 buffer；键盘与剪贴板处理复用既有上下文，验证输入焦点、选中复制和多终端切换。

## 验证外观与操作

选与改动相关的真实页面或 Storybook：亮/暗主题、支持的密度、窄窗口/缩放、长文本、空/加载/失败/禁用/选中/聚焦状态；测试键盘操作与焦点返回。保存有代表性的前后截图，说明哪些状态已实际检查。

浏览器/Storybook 适合组件布局验证；Electron 窗口拖动、原生菜单、preload、终端和系统快捷键需要实际桌面流程。静态源码检查不能宣称视觉一致。

来源：[UI kit](https://github.com/generalaction/emdash/blob/main/agents/conventions/ui-kit.md)、[UI styling](https://github.com/generalaction/emdash/blob/main/agents/conventions/ui-styling.md)、[Renderer patterns](https://github.com/generalaction/emdash/blob/main/agents/conventions/renderer-patterns.md)、[Chat architecture](https://github.com/generalaction/emdash/blob/main/packages/chat-ui/ARCHITECTURE.md)、[产品快捷键](https://emdash.com/docs/keyboard-shortcuts)。
