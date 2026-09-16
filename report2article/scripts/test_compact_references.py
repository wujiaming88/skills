#!/usr/bin/env python3
"""Offline fixtures for the template's illustrative @O/@C/@L notation.

This test-local resolver checks reference shape only. It is NOT a production
checklist parser, article generator, semantic validator, or weekly_ops entry.
Existing ledgers need not adopt this notation. Semantic counterexamples require
side-by-side review with the frozen source; resolving every ID is insufficient.
"""
import re
import unittest

TOKEN = re.compile(r'@([^\s；，。|]+)')
KEY = re.compile(r'[OCL][0-9]+\Z')


def expand_fixture(rows, item):
    """Resolve direct references within ONE fixture; reject semantic chains."""
    definitions = {}
    for key, text in rows:
        if not KEY.fullmatch(key) or key in definitions:
            raise ValueError('invalid or duplicate local definition')
        if TOKEN.search(text):
            raise ValueError('definitions must be terminal: no cycle or deep chain')
        definitions[key] = text

    def resolve(match):
        key = match.group(1)
        if not KEY.fullmatch(key) or key not in definitions:
            raise ValueError('dangling, cross-list or indirect reference')
        return definitions[key]

    return TOKEN.sub(resolve, item)


class CompactReferenceFixtures(unittest.TestCase):
    def setUp(self):
        self.rows = [
            ('O01', '甲公司'),
            ('C01', '报告期内；据甲公司披露；计划，非实际交付；母稿§2第1段'),
            ('L01', '甲公司公告 https://example.invalid/notice；直接支撑D01，不支持实际交付结论'),
        ]
        self.item = '@O01；计划交付上限100台；@C01；@L01'

    def test_direct_local_references_expand(self):
        text = expand_fixture(self.rows, self.item)
        self.assertNotIn('@', text)
        self.assertIn('计划交付上限100台', text)
        self.assertIn('计划，非实际交付', text)
        self.assertIn('https://example.invalid/notice', text)

    def test_dangling_reference_rejected(self):
        with self.assertRaises(ValueError):
            expand_fixture(self.rows, '@O99；100台')

    def test_duplicate_definition_rejected(self):
        with self.assertRaises(ValueError):
            expand_fixture(self.rows + [('O01', '乙公司')], self.item)

    def test_cycle_rejected(self):
        with self.assertRaises(ValueError):
            expand_fixture([('C01', '@C02'), ('C02', '@C01')], '@C01')

    def test_deep_chain_rejected(self):
        with self.assertRaises(ValueError):
            expand_fixture([('C01', '@C02'), ('C02', '据公司披露')], '@C01')

    def test_cross_list_reference_rejected(self):
        with self.assertRaises(ValueError):
            expand_fixture(self.rows, '@second:C01')

    def test_other_atom_cannot_supply_inherited_semantics(self):
        with self.assertRaises(ValueError):
            expand_fixture(self.rows, '@F01')

    def test_separate_lists_have_separate_definitions(self):
        # Same local ID in independent lists is valid, not evidence of equivalence.
        first = expand_fixture([('O01', '甲公司')], '@O01')
        second = expand_fixture([('O01', '乙公司')], '@O01')
        self.assertNotEqual(first, second)

    def test_resolved_and_same_count_can_still_lose_upper_bound(self):
        # Deliberate semantic defect passes reference-shape checking.
        # The reviewer, not this resolver, must reject "actual" for "planned".
        wrong = '@O01；实际交付100台；@C01；@L01'
        self.assertEqual(len(TOKEN.findall(self.item)), len(TOKEN.findall(wrong)))
        self.assertIn('实际交付100台', expand_fixture(self.rows, wrong))

    def test_source_backlinks_are_not_inheritance(self):
        # L's plain support IDs index the relationship; they do not form @ chains.
        self.assertIn('直接支撑D01', expand_fixture(self.rows, '@L01'))


if __name__ == '__main__':
    unittest.main(verbosity=2)
