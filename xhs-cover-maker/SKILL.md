---
name: xhs-cover-maker
description: "把 xhs-content-forge 的配图清单渲染成小红书封面/配图(4x高清、文字清晰)。固定五岳AI公司视觉IP,5套版式:封面×3(大字报/对比/看板)+内页×2(要点图/金句卡)。用于小红书出封面/做配图/渲染笔记图。"
---

# 小红书封面/配图工厂 · xhs-cover-maker

把「配图清单」变成成品图。**确定性渲染**:用 WeasyPrint(纯 Python,不依赖浏览器)把 HTML/CSS 渲成 PDF,再经 poppler 超采样栅格化为高清 PNG,把"设计"降级成"填空出图"。固定五岳视觉 IP,文字永远清晰(AI 直出图做不到)。

> ⚠️ 本宿主机 chromium 被容器 sandbox 杀(zygote/network crashed),故弃用 Playwright 改用 WeasyPrint 链路。详见 workspace/xhs-output/RENDER_REPORT.md。

不做创意设计决策——版式和配色已定死,只负责填内容、渲染、交付。需要纯艺术海报时才考虑 canvas-design。

## 什么时候用

- content-forge 产出了配图清单,要出封面/内页图
- 要小红书竖版封面(1080×1440,3:4)或配图
- 要保证图上文字清晰可读(数据/标题/对话)

## 五套版式(3 套封面 + 2 套内页,对应作战手册封面公式)

**封面(首图,1080×1440):**

| 版式 | 模板 | 适用栏目 | 特征 |
|------|------|---------|------|
| **大字报** | `assets/cover_dazibao.html` | ③翻车 / ④教程 / ②人设 | 超大主标题(≤12字)占画面50%+,纯色/渐变底,关键词高亮 |
| **对比** | `assets/cover_duibi.html` | ①成果 / 反差 | 左右分屏「需求 vs 成品」「人 vs AI」 |
| **看板** | `assets/cover_kanban.html` | ①数据成果 | 终端/仪表盘风,数据卡片 + 高亮重点 |

**内页(P2-P9,同尺寸 1080×1440):**

| 版式 | 模板 | 用途 | 特征 |
|------|------|---------|------|
| **要点信息图** | `assets/cover_neiye_point.html` | 干货拆条(P2-P5) | 标题 + 3-4 个要点条目(emoji 序号),留白克制 |
| **金句卡** | `assets/cover_neiye_quote.html` | 收尾图(P9) | 一句话金句大字 + 署名「—— 五岳AI公司」,引收藏/转发 |

五套共用 `assets/brand.css`(五岳视觉 IP:配色 + logo 角标 + 字体链 + 高亮词机制 + 防溢出工具)。

## 占位符体系(content-forge → cover-maker 无缝衔接)

每个模板顶部注释**列全了自己的 `{{...}}` 占位符**,命名统一(`{{TITLE}}` / `{{SUB}}` / `{{SECTION}}` / `{{Pn_*}}` 等)。content-forge 输出的「封面变量」直接逐个映射,不用猜。

**高亮词机制(三档,brand.css 内置)**——让用户能指定某词强调:

| 写法 | 效果 |
|------|------|
| `<span class="hl">词</span>` | 描绿 |
| `<span class="hl-amber">词</span>` | 描橙 |
| `<span class="hl-box">词</span>` | 绿底色块(最抢眼,留给最狠的那个词) |
| `<span class="hl-box-amber">词</span>` | 橙底色块 |

**防溢出**:模板已给文本挂 `.fit`(长词自动换行断词)和 `.clamp-2/.clamp-3`(副标/正文限行省略号)。标题超长时:大字报加 `class="title t-long"`(缩到 104px)、金句卡加 `class="quote q-long"`(缩到 62px),防止填满 12 字 / 两行副标时爆版。

**空块自动隐藏**:要点图有 4 个点位、看板有多张数据卡,只填一部分时,渲染脚本会自动删除仍残留 `{{...}}` 未填充占位符的 `.point` / `.stat` 块——填几个点就出几个,不会出现空卡片。

## 工作流

1. **挑版式**:按配图清单里标注的版式选模板(封面:大字报/对比/看板;内页:要点图/金句卡)。
2. **填内容**:复制对应 `assets/*.html` 到工作目录,按模板顶部注释里列出的 `{{...}}` 占位符逐个填。content-forge 的「封面变量」直接映射过来。主标题 ≤12 字,关键词用 `<span class="hl">`/`hl-amber`/`hl-box` 高亮(见下高亮词机制)。文案超长时挂 `t-long`/`q-long` 防溢出。
3. **渲染**:用本 skill 的脚本出高清竖版图。
   ```bash
   python3 scripts/render_cover.py <填好的.html> <输出.png>
   ```
   默认竖版 1080×1440(小红书 3:4)、3x 超采样。底层 WeasyPrint→PDF→pdftocairo 栅格化→Pillow LANCZOS 下采样。
   - **重要**:填好的 HTML 必须与 `brand.css` 同目录(或保证 `href="brand.css"` 相对路径可解析),否则 CSS 变量失效会导致文字/配色全丢、整图变纯深底。建议直接复制 assets 内的模板就地改、就地渲。
   - 依赖(本机已装):weasyprint、poppler-utils(pdftocairo)、Pillow、Noto Sans CJK SC 字体。
4. **控大小**:>5MB 自动转 JPEG(quality 92)。脚本已内置 `--jpeg` 选项。
5. **交付**:输出 `MEDIA:<path>`;Telegram 发原图用 `--force-document` 避免压缩。

## 视觉 IP 铁律(改了就丢失辨识度,别动)

- **配色**:深色科技底(炭黑 #0E1116 / 深墨绿)+ 荧光绿强调 #00E676 / 橙黄 #FFAB00,贴 AI/终端气质,区别于美妆白底流。
- **logo 角标**:每张图右下角固定"🏔 五岳AI公司"角标(brand.css 已内置)。
- **字体**:`"PingFang SC","Microsoft YaHei","Noto Sans SC","Noto Sans CJK SC",sans-serif,"Noto Color Emoji"`,保证中文渲染;末尾 `Noto Color Emoji` 让 🏔📝🎯🛠⚡💬✓ 等 emoji 在 WeasyPrint 下出彩色字形(实测不是空白框)。
- **文字排版**:主标题 ≤12字一眼读完;关键词描黄/描绿;最多 3 字号层级,别堆字。
- **尺寸**:封面竖版 3:4(1080×1440)。内页可 1:1 或 3:4。

## 注意

- 不出现真人(不露脸)。需要"人"的元素用山峰/终端/对话气泡等抽象呈现。
- 图上**绝不**出现微信号/二维码/联系方式(平台导流红线)。
- 文字必须清晰:这是用渲染而非 AI 直出的唯一理由,别省 4x。
