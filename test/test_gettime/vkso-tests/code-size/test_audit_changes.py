#!/usr/bin/env python3
import unittest
from audit_changes import lexical_lines, ranges


class SourceCountingTests(unittest.TestCase):
    def test_comments_do_not_consume_string_literals(self):
        source = 'char *url = "https://host/*text*/"; // comment\n/* multi\nline */ int x;\n\n'
        self.assertEqual(lexical_lines('sample.c', source),
                         [(1, 'char *url = "https://host/*text*/" ;'), (3, 'int x;')])

    def test_comment_only_change_has_no_code_change(self):
        old = 'int value; /* previous explanation */\n'
        new = '  int   value; /* updated explanation */\n'
        self.assertEqual(lexical_lines('sample.c', old), lexical_lines('sample.c', new))

    def test_kconfig_help_is_not_code(self):
        source = 'config TEST\n\tbool "test"\n\thelp\n\t  prose\n\nconfig NEXT\n\tbool\n'
        self.assertEqual([n for n, _ in lexical_lines('Kconfig', source)], [1, 2, 6, 7])

    def test_assembler_keeps_preprocessor_and_labels(self):
        self.assertEqual(len(lexical_lines('entry.S', '#include <header.h>\n/* note */\nentry:\n\tret\n')), 3)

    def test_ranges_reject_stale_and_overlapping_selection(self):
        self.assertEqual(ranges('1-2,4', 4), {1, 2, 4})
        for spec in ('0', '3-2', '1-5', '1-2,2'):
            with self.subTest(spec=spec), self.assertRaises(ValueError):
                ranges(spec, 4)


if __name__ == '__main__':
    unittest.main()
