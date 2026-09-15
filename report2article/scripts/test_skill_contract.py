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

if __name__ == '__main__':
    unittest.main(verbosity=2)
