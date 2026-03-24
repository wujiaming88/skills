---
name: ppt-from-template
description: "两阶段 PPT 创建：先与用户规划内容生成 plan.yaml，再交子代理执行。触发词：模板、PPT、课件、演示文稿、幻灯片、做个PPT。依赖 pptx Skill 的脚本。"
---

# PPT 模板创建 Skill（两阶段工作流）

## 核心思路

**把「内容规划」和「PPT 制作」彻底解耦。**

```
阶段 1：规划（主会话）          阶段 2：制作（子代理）
┌─────────────────────┐      ┌─────────────────────┐
│ 分析模板布局         │      │ 读 plan.yaml        │
│ 与用户讨论内容       │  →   │ 解包模板            │
│ 生成 plan.yaml      │      │ 逐页填充            │
│                     │      │ 打包 + QA           │
└─────────────────────┘      └─────────────────────┘
 上下文：轻量                  上下文：独立子代理
 不碰 XML                     不需要来回讨论
```

## 目录约定

```
模板目录: /root/.openclaw/workspace-cbz001/template/
输出目录: /root/.openclaw/workspace-cbz001/output/
计划文件: /root/.openclaw/workspace-cbz001/plan.yaml
临时目录: /tmp/ppt-work/
pptx 脚本: ~/.openclaw/skills/pptx/scripts/
```

---

## 阶段 1：规划（主会话完成）

目标：和用户一起确定内容，生成 `plan.yaml`。**全程不碰 XML。**

### 1.1 分析模板布局

```bash
# 生成缩略图（查看每页长什么样）
python ~/.openclaw/skills/pptx/scripts/thumbnail.py \
  "/root/.openclaw/workspace-cbz001/template/模板文件.pptx"

# 提取文本（了解占位符内容）
python -m markitdown "/root/.openclaw/workspace-cbz001/template/模板文件.pptx"
```

把缩略图发给用户看，一起确认：
- 模板有哪些可用版式（封面、目录、内容、数据、分隔、结尾等）
- 每种版式的 slide 编号是什么（如 slide3 = 封面，slide7 = 目录）

### 1.2 讨论内容结构

与用户确定：
- 总共需要几页
- 每页用哪个版式
- 每页填什么内容（标题、正文、数据、图片等）

### 1.3 生成 plan.yaml

根据讨论结果，生成中间文件：

```yaml
# plan.yaml
template: /root/.openclaw/workspace-cbz001/template/培训课模板.pptx
output: /root/.openclaw/workspace-cbz001/output/最终文件名.pptx

slides:
  - source: slide3.xml      # 模板中的封面页
    role: cover
    content:
      title: "2026 年度战略报告"
      subtitle: "市场拓展与技术升级"
      date: "2026年3月"

  - source: slide7.xml       # 模板中的目录页
    role: toc
    content:
      items:
        - "一、市场现状分析"
        - "二、竞争格局"
        - "三、战略规划"
        - "四、执行路径"

  - source: slide12.xml      # 双栏图文布局
    role: content
    content:
      title: "一、市场现状分析"
      body: |
        2025 年行业整体规模达到 520 亿，
        同比增长 18%...

  - source: slide5.xml       # 数据展示页
    role: stats
    content:
      title: "关键指标"
      stats:
        - label: "营收增长"
          value: "+42%"
        - label: "客户数"
          value: "1,200+"
        - label: "市场份额"
          value: "23%"

  - source: slide5.xml       # 同一布局可复用
    role: stats
    content:
      title: "技术投入"
      stats:
        - label: "研发占比"
          value: "18%"
        - label: "专利数"
          value: "86"

  - source: slide20.xml      # 结尾页
    role: ending
    content:
      title: "谢谢"
      contact: "xxx@company.com"
```

### plan.yaml 字段说明

| 字段 | 作用 |
|------|------|
| `template` | 模板文件绝对路径 |
| `output` | 输出文件绝对路径 |
| `slides` | 页面列表，按顺序排列 |
| `slides[].source` | 用模板中哪个 slide 做版式（从缩略图确认） |
| `slides[].role` | 语义标记（cover/toc/content/stats/section/ending 等） |
| `slides[].content` | 该页所有需要填入的文本、数据、图片路径 |

**关键**：plan.yaml 是人可读的，用户确认满意后再交子代理执行。修改成本极低——改 YAML 重跑就行。

---

## 阶段 2：制作（子代理执行）

确认 plan.yaml 后，派子代理执行。子代理有独立上下文，不受主会话历史影响。

### 子代理任务 Prompt 模板

```
根据 plan.yaml 创建 PPT。

plan.yaml 路径: /root/.openclaw/workspace-cbz001/plan.yaml
pptx 脚本目录: ~/.openclaw/skills/pptx/scripts/
编辑规则参考: ~/.openclaw/skills/pptx/editing.md

执行步骤：

1. 读取 plan.yaml
2. 解包模板到 /tmp/ppt-work/unpacked/
3. 根据 plan 裁剪模板：只保留 source 中引用的 slide，删除其余页
4. 复制需要复用的 slide（同一 source 被多个 plan entry 引用时）
5. 按 plan 顺序排列 slide
6. 逐页编辑内容：
   - grep 定位占位符文本位置
   - 用 edit 工具精确替换，不整页 read
   - 保留原有格式属性
7. 清理孤立文件: python scripts/clean.py
8. 打包: python scripts/office/pack.py --original
9. 压缩: python scripts/compress_pptx.py（如果有）
10. 移动到 output 路径

注意：
- 使用 edit 工具进行所有修改，不用 sed
- 中文引号用 XML 实体：&#x201C; &#x201D;
- 保留 <a:pPr> 格式属性
- 多条目用多个 <a:p> 元素
```

### 派发方式

```python
sessions_spawn({
    task: "根据 plan.yaml 创建 PPT...",  # 上面的 Prompt
    agentId: "waicode",
    label: "PPT-MAKE",
    runTimeoutSeconds: 600
})
```

---

## 修改与迭代

plan.yaml 最大的优势是**改内容不需要重新编辑 XML**：

| 场景 | 操作 |
|------|------|
| 改某页文字 | 编辑 plan.yaml 对应 content → 重跑子代理 |
| 加一页 | 在 plan.yaml 插入一个 slide entry → 重跑 |
| 删一页 | 删掉 plan.yaml 对应 entry → 重跑 |
| 换版式 | 改 source 字段 → 重跑 |
| 换模板 | 改 template 路径 + 重新映射 source → 重跑 |
| 批量生产 | 复制 plan.yaml，只改 content → 批量跑 |

---

## 优化速查表

| 问题 | 方法 |
|------|------|
| 模板太大 | 阶段 2 先裁剪，只保留 plan 引用的页 |
| XML 太大 | grep 定位占位符 → edit 精确替换 |
| 页数太多 | 子代理并行（每个处理 2-3 页） |
| 上下文不够 | 逐页处理，不批量 read |
| QA 太贵 | 只渲染改过的页，子代理做视觉检查 |
| 文件太大 | compress_pptx.py 重压缩 + 图片优化 |

## 注意事项

- **备份**：操作前始终保留原始模板，不修改 template/ 目录中的文件
- **临时目录**：所有解包/编辑在 /tmp/ppt-work/ 进行
- **超时**：大文件操作设 600s 超时
- **打包**：用 `--original` 参数保留原始媒体压缩方式
