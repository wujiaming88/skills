#!/usr/bin/env python3
"""Offline template-structure regressions, not an article semantic acceptance.

These checks keep the default form compact while preserving detailed exceptions
and fidelity gates. Local reference behavior is covered by test_compact_references.
No frozen report, installed skill, network, or production workflow is modified.
"""
from pathlib import Path
import re
import unittest

from test_compact_references import expand_fixture

ROOT = Path(__file__).resolve().parents[1]


def sections(text):
    headings = list(re.finditer(r'^## (\d+)\. (.+)$', text, re.MULTILINE))
    return {
        int(match[1]): text[match.end():headings[i + 1].start() if i + 1 < len(headings) else len(text)]
        for i, match in enumerate(headings)
    }


def table_rows(text):
    return [tuple(cell.strip() for cell in line.strip('|').split('|'))
            for line in text.splitlines() if line.startswith('|')]


class ChecklistTemplateTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.template = (ROOT / 'references/info-checklist-template.md').read_text()
        cls.parts = sections(cls.template)

    def test_six_stage_structure_remains(self):
        headings = re.findall(r'^## (\d+)\. (.+)$', self.template, re.MULTILINE)
        self.assertEqual(headings, [
            ('1', '建立基线'), ('2', '记录去向及语义映射'), ('3', '正向覆盖'),
            ('4', '全文反向溯源'), ('5', '独立二次派生与补漏'), ('6', '交付口径'),
        ])

    def test_baseline_form_itself_uses_local_definitions(self):
        form = self.parts[1].split('```markdown', 1)[1].split('```', 1)[0]
        self.assertIn('共同限定 C', form)
        self.assertIn('不另计事实', form)
        for kind in ('F', 'D', 'J'):
            row = next(line for line in form.splitlines() if f'{kind}01：' in line)
            for ref in ('@O01', '@C01', '@L01'):
                self.assertIn(ref, row)
        self.assertIn('只引用实际适用', self.parts[1])
        self.assertIn('本条特有限定', self.parts[1])

    def test_default_mapping_table_is_compact_not_a_third_inventory(self):
        rows = table_rows(self.parts[2])
        self.assertEqual(rows[0], (
            '首次编号', '二次编号', '母稿准确定位 / 必要消歧',
            '内容去向 / 准确文章落点', '状态',
        ))
        self.assertGreaterEqual(len(rows), 6)  # header, delimiter, F/D/J/L examples
        self.assertTrue(all(len(row) == 5 for row in rows))
        self.assertNotIn('母稿位置与完整语义', self.parts[2])
        for row in rows[2:]:
            self.assertRegex(row[0], r'[FDJL]\d+')
            self.assertRegex(row[1], r'[FDJL]\d+')
            self.assertIn('§', row[2])
            self.assertIn('：', row[3])
            self.assertIn(row[4], ('等义', '待核'))
        self.assertIn('只做映射', self.parts[2])

    def test_plain_splits_and_merges_do_not_force_long_recopying(self):
        part = self.parts[2]
        for term in ('普通一对多、多对一或跨类别等义对应', '仍用紧凑行',
                     '不因对应形态本身要求详写', '不整段重写双方原文'):
            self.assertIn(term, part)
        self.assertNotIn('跨类别、一对多/多对一、补漏、来源争议或判断差异则详细', part)

    def test_exception_detail_is_separate_and_evidence_bearing(self):
        part = self.parts[2]
        self.assertIn('### 仅真实差异详记', part)
        for term in ('真实漏项', '跨类别复杂拆合', '来源争议', '判断变化',
                     '双方实际承载', '缺失或差异', '母稿依据', '处理结果',
                     '只摘必要差异', '差异编号'):
            self.assertIn(term, part)

    def test_exact_locations_are_bound_to_versions(self):
        part = self.parts[2]
        for term in ('双方清单路径及冻结版本', '文章路径及版本', '重复标题',
                     '段落/句序或表格行列', '必要消歧', '实际行或锚点', '不串联多层映射'):
            self.assertIn(term, part)

    def test_mapping_is_not_semantic_inheritance(self):
        for term in ('两份独立清单不能共享', '跨清单引用', '定义中不再转引',
                     '来源反列支撑编号是关系索引', '逐项打开两侧条目',
                     '不能因母稿或文章已写就虚称原清单已记',
                     '不能反向补足任一原清单缺失的语义'):
            self.assertIn(term, self.template)

    def test_fidelity_dimensions_and_no_hard_caps_remain(self):
        for term in ('主体', '期间', '单位', '统计口径', '分母/样本', '归因',
                     '限定', '判断强弱', '母稿定位', '来源支撑', '金额上限',
                     '计划/实际', '未确认/不存在', '来源直接/间接支撑', '非新法',
                     '不设清单字数或条目硬上限', '不证明等义'):
            self.assertIn(term, self.parts[1])

    def test_original_counts_and_append_only_gap_handling_remain(self):
        for term in ('原始清单和计数', '补漏区追加新编号及证据', '不覆盖原计数',
                     '不重写清单凑数', '差异未解不得PASS'):
            self.assertIn(term, self.parts[5])
        self.assertIn('不能计数齐平', self.parts[2])
        self.assertIn('无源增写须回母稿纠正', self.parts[2])

    def test_public_and_forward_reverse_checks_remain(self):
        for term in ('实质信息只能映射正文或公开补充材料', '关键限制不能只放附录',
                     '抓取过程与由其形成的证据缺口分开处理'):
            self.assertIn(term, self.parts[2])
        self.assertIn('逐项核对两份清单', self.parts[3])
        self.assertIn('从头到尾逐段反查公开内容', self.parts[4])
        self.assertIn('标题、导语、正文、过渡、结尾、图表、图注、附录', self.parts[4])

    def test_completion_references_evidence_without_reprinting(self):
        part = self.parts[6]
        for term in ('完成标记和父级审计', '直接指向', '不再全文重抄',
                     '共同条件或证据', '冻结版本', '计数', '未销账数', '状态'):
            self.assertIn(term, part)

    def test_both_final_readers_and_reading_review_stay_mandatory(self):
        part = self.parts[6]
        for term in ('不减少编辑者和父级', '完整读取', '两份清单、映射和文章全文',
                     '正向覆盖与全文反向溯源', 'reading-review.md', '完整新版',
                     '不能只看完成标记或差异摘要'):
            self.assertIn(term, part)


class FidelityReferenceFixtures(unittest.TestCase):
    """Synthetic shape fixtures; values are NOT facts from the frozen weekly."""

    def test_money_period_attribution_and_source_boundary_survive_expansion(self):
        rows = [
            ('O01', '甲公司'),
            ('C01', '2026年上半年；据甲公司披露；计划采购，非实际支出；限试点10家；母稿§2第1段'),
            ('L01', '甲公司公告 https://example.invalid/budget；直接支撑D01计划额度，不支持实际支出'),
        ]
        text = expand_fixture(rows, '@O01；预算上限人民币500万元；@C01；@L01')
        for term in ('上限人民币500万元', '2026年上半年', '据甲公司披露', '非实际支出',
                     '限试点10家', '母稿§2第1段', '不支持实际支出'):
            self.assertIn(term, text)

    def test_other_list_definition_cannot_fill_a_local_gap(self):
        first = [('O01', '甲公司'), ('C01', '计划采购，非实际支出')]
        second = [('O01', '甲公司')]
        self.assertIn('计划采购', expand_fixture(first, '@O01；@C01'))
        with self.assertRaises(ValueError):
            expand_fixture(second, '@O01；@C01')

    def test_same_ids_and_counts_do_not_prove_common_condition_equivalence(self):
        first = [('C01', '预算上限；计划采购；据公司披露')]
        second = [('C01', '实际支出；已经付款；独立实测')]
        self.assertEqual(len(first), len(second))
        self.assertNotEqual(expand_fixture(first, '@C01'), expand_fixture(second, '@C01'))
        # Both resolve: only source-based semantic review can reject the drift.


if __name__ == '__main__':
    unittest.main(verbosity=2)
