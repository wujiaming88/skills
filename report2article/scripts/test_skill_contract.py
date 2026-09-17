#!/usr/bin/env python3
"""Static rule-regression checks; not a substitute for article semantic review."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]

class ContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.main = (ROOT / 'SKILL.md').read_text()
        cls.refs = {p.name: p.read_text() for p in (ROOT / 'references').glob('*.md')}
        cls.all = cls.main + '\n'.join(cls.refs.values())

    def test_frontmatter(self):
        head = self.main.split('---', 2)[1]
        self.assertIn('name: "report2article"', head)
        for term in ('报告转文章', '文章阅读优化', '结构', '表达', '配图'):
            self.assertIn(term, head)
        self.assertLess(len(self.main), 10000)

    def test_reference_resolution(self):
        refs = set(re.findall(r'references/[A-Za-z0-9._/-]+\.md', self.main))
        self.assertGreaterEqual(len(refs), 7)
        for ref in refs:
            self.assertTrue((ROOT / ref).is_file(), ref)

    def test_fidelity_and_authorization(self):
        for term in ('语义保真', '编辑自由', '等义', '判断强弱', '研究授权'):
            self.assertIn(term, self.main)
        for forbidden in ('正文内容一字不动', '内容层一字不动', '只重组排序起标题'):
            self.assertNotIn(forbidden, self.all)

    def test_headings_are_optional_navigation(self):
        for term in ('编辑分块不等于文章分节', '不强求句式一致', '不设标题数量配额', '短文可无子标题', '多主题周报'):
            self.assertIn(term, self.main)
        self.assertNotIn('同级标题句式一致', self.all)
        self.assertNotIn('相近的抽象层级和标题句式', self.all)
        self.assertIn('粗体小标题', self.main)

    def test_heading_balance_in_both_directions(self):
        for term in ('双向检查', '恢复必要层次', '子问题边界', '各章节可按内容采用不同深度', '不把清零或减少某级标题作为优化目标'):
            self.assertIn(term, self.main)
        review = self.refs['reading-review.md']
        for term in ('过密分节', '层次缺失', '拆分、合并或不拆的理由', '短而单一', '回查困难'):
            self.assertIn(term, review)

    def test_structure_approval_precedes_render_checks(self):
        review = self.refs['reading-review.md']
        for term in ('绑定最终稿版本', '层级合法', '标题ID唯一', '目录目标可达', '不只从待测页面反向生成预期', '不评价标题多少优劣'):
            self.assertIn(term, review)
        self.assertIn('标题数量与程序通过不代替阅读判断', self.main)

    def test_public_information_cannot_be_hidden(self):
        for term in ('实质信息', '公开补充材料', '准确可访问落点', '不能移入折叠区', '无法确定能否移出时先保留公开'):
            self.assertIn(term, self.main)
        mapping = self.refs['info-checklist-template.md']
        for term in ('内容去向', '处理理由', '关键限制不能只放附录', '抓取过程与由其形成的证据缺口分开'):
            self.assertIn(term, mapping)

    def test_opening_and_ending(self):
        for term in ('开头直接进入', '不占导语', '非实测性质', '局部beta', '以最后一个实质段落结束', '不写入文章首尾'):
            self.assertIn(term, self.main)

    def test_independent_lists_and_reuse(self):
        protocol = self.refs['long-report-protocol.md']
        for term in ('不看首次账本或成稿', '两份清单完成冻结后再协调', '一对多', '多对一', '不重写凑数', '未销账0', '不能声称重新做了盲提取'):
            self.assertIn(term, protocol)

    def test_reading_review_and_recheck(self):
        review = self.refs['reading-review.md']
        for term in ('读完整篇', '首尾', '受影响', '完整新版本', '不以抽查', '引用跳转和已有深链接'):
            self.assertIn(term, review)
        self.assertIn('最终验收仍覆盖完整新版', self.main)

    def test_visual_authorization_and_fallback(self):
        visual = self.refs['visual-guidelines.md']
        for term in ('认知负担', '不得编造', '来源', '替代文本', '用户明确要求', '配图方案', '独立交付说明', '查看实际图片'):
            self.assertIn(term, visual)

    def test_style_and_relationships(self):
        prose = self.refs['prose-style.md']
        for term in ('整篇只选一个主风格', '专业通俗', '技术深度', '媒体叙事', '周报速读'):
            self.assertIn(term, prose)
        self.assertIn('明确表达', self.refs['logic-skeleton.md'])
        self.assertIn('未明确关系', self.refs['logic-skeleton.md'])

    def test_compact_definition_contract(self):
        template = self.refs['info-checklist-template.md']
        for term in ('单处定义与短引用', '两份独立清单不能共享', '@O01', '@C01', '@L01',
                     '一次直接定位', '定义中不再转引', '悬空、循环、深链', '不设清单字数或条目硬上限',
                     '引用能解析仅证明可定位，不证明等义'):
            self.assertIn(term, template)
        self.assertIn('只按该模板第1—2节', self.main)

    def test_mapping_differences_not_count_parity(self):
        template = self.refs['info-checklist-template.md']
        for term in ('等义且无差异项短记', '双方编号', '准确文章落点', '状态',
                     '真实漏项', '跨类别复杂拆合', '来源争议', '判断变化', '逐项打开两侧条目',
                     '不能因母稿或文章已写就虚称原清单已记', '不能计数齐平',
                     '无源增写须回母稿纠正', '来源直接/间接支撑', '非新法'):
            self.assertIn(term, template)

    def test_continuation_requires_context_and_reading_evidence(self):
        protocol = self.refs['long-report-protocol.md']
        for term in ('同一编辑者连续阶段', '母稿与所用规则SHA均未变',
                     '前次完整读取证据齐全', '所需上下文确实仍在', '前次读取范围及末尾定位',
                     '同session或SHA相同本身不证明', '换人、缺上下文、版本变化或读取证据不足',
                     '所必需文件的完整读取', '新到的第二清单仍须完整读完'):
            self.assertIn(term, protocol)

    def test_phase1_is_handoff_not_final_semantics(self):
        protocol = self.refs['long-report-protocol.md']
        for term in ('父级中间Phase1仅核交接完整性', '两原清单冻结版本', '写权已交回',
                     '明确阻断项', '读取尾部/截断状态', '已有具体疑点即读取受影响内容',
                     '不把中间检查标成文章PASS', '由原编辑继续协调'):
            self.assertIn(term, protocol)

    def test_final_full_reads_and_private_boundary_unchanged(self):
        protocol = self.refs['long-report-protocol.md']
        for term in ('编辑者完成协调后完整读取', '父级最终也须完整读取冻结母稿',
                     '两份清单、映射与文章', '不能只看done、差异摘要',
                     '私密内容仍不传给编辑', '第6节编辑者和父级最终全文验收仍完整执行'):
            self.assertIn(term, protocol)
        self.assertIn('执行`reading-review.md`完整阅读', protocol)

if __name__ == '__main__':
    unittest.main(verbosity=2)
