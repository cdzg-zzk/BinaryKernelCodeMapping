#!/usr/bin/env python3
"""Adversarial checks for the evidence counter's scope and ownership rules."""
import copy
import json
import unittest

from audit_current import inventory


class InventoryTests(unittest.TestCase):
    def setUp(self):
        self.row = dict(id='S1', system='Raw', origin='Raw', path='sample.c',
                        scope='feature', category='computation', component='time',
                        ranges='1-4', symbols='sample', reason='test fixture')
        self.text = '/* comment\ncontinued */\nconst char *s = "/* literal */"; // comment\nint x;\n'

    def test_comments_and_string_literals_do_not_inflate_or_erase_code(self):
        result = inventory({'revision':'test','slices':[self.row]}, {('Raw','sample.c'):self.text})
        count = json.loads(result['source-totals.json'])
        self.assertEqual(count['totals']['Raw']['feature'], 2)
        self.assertIn('literal', result['source-lines.csv'])

    def test_overlap_across_categories_is_rejected(self):
        other = copy.deepcopy(self.row)
        other.update(id='S2', category='adapter', ranges='3-4')
        with self.assertRaisesRegex(ValueError, 'double ownership'):
            inventory({'revision':'test','slices':[self.row,other]}, {('Raw','sample.c'):self.text})

    def test_out_of_file_range_cannot_silently_truncate(self):
        self.row['ranges'] = '1-5'
        with self.assertRaisesRegex(ValueError, 'invalid range'):
            inventory({'revision':'test','slices':[self.row]}, {('Raw','sample.c'):self.text})


if __name__ == '__main__':
    unittest.main(verbosity=2)
