#!/usr/bin/env python3
"""Linked-image IDs: real link variants and malformed ELF notes."""
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import build_PIC_so as B


def note(payload=b'\x12\xab\x00', name=b'GNU\0', kind=3):
    return (struct.pack('<III', len(name), len(payload), kind) + name +
            bytes((-len(name)) % 4) + payload + bytes((-len(payload)) % 4))


class BuildIdentityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='vkso-build-id-')
        cls.root = Path(cls.temp.name)
        manager = Path(__file__).resolve().parents[2] / 'page_cache_replace/manager.cpp'
        harness = cls.root / 'notes.cpp'
        harness.write_text('#define main manager_program_main\n#include "' + str(manager) + '"\n'
                           '#undef main\nint main(int argc, char **argv) {\n'
                           'std::string id; if (argc != 2 || !note_build_id(argv[1], id)) return 1;\n'
                           'printf("%s\\n", id.c_str()); return 0; }\n')
        cls.reader = cls.root / 'reader'
        subprocess.run(['g++', '-std=c++17', harness, '-o', cls.reader], check=True)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def cpp_parse(self, data):
        path = self.root / 'notes.bin'
        path.write_bytes(data)
        return subprocess.run([self.reader, path], capture_output=True, text=True)

    def test_alignment_and_unrelated_notes(self):
        data = note(b'other', b'Linux\0', 1) + note() + b'\0\0'
        self.assertEqual(B.gnu_build_id_notes(data), ['12ab00'])
        result = self.cpp_parse(data)
        self.assertEqual((result.returncode, result.stdout.strip()), (0, '12ab00'))

    def test_malformed_notes(self):
        for data in (b'\x01', note()[:-2], note(b''), note(bytes(65)),
                     struct.pack('<III', 0xffffffff, 20, 3)):
            with self.subTest(data=data[:12]):
                with self.assertRaises(ValueError): B.gnu_build_id_notes(data)
                self.assertNotEqual(self.cpp_parse(data).returncode, 0)

    def test_missing_or_duplicate_ids(self):
        for data in (note(name=b'other\0'), note()+note()):
            self.assertNotEqual(len(B.gnu_build_id_notes(data)), 1)
            self.assertNotEqual(self.cpp_parse(data).returncode, 0)

    def test_real_linked_variants_and_missing_id(self):
        source = self.root / 'same.c'
        source.write_text('int main(int argc, char **argv) { return argc * argc + (argv == 0); }\n')
        ids = []
        for opt in ('-O0', '-O2'):
            output = self.root / opt
            subprocess.run(['gcc', opt, '-Wl,--build-id=sha1', source, '-o', output], check=True)
            ids.append(B.elf_build_id(output))
        self.assertNotEqual(*ids)
        output = self.root / 'no-id'
        subprocess.run(['gcc', '-Wl,--build-id=none', source, '-o', output], check=True)
        with self.assertRaisesRegex(ValueError, 'found 0'): B.elf_build_id(output)
        duplicate = self.root / 'duplicate.bin'
        duplicate.write_bytes(note())
        subprocess.run(['objcopy', '--add-section', f'.note.extra={duplicate}', '--set-section-flags',
                        '.note.extra=alloc,readonly', self.root / '-O2', self.root / 'two-ids'], check=True,
                       capture_output=True)
        # objcopy creates PROGBITS for new sections; convert to NOTE in the
        # section header so the reader tests the real ELF-level duplicate rule.
        data = bytearray((self.root / 'two-ids').read_bytes())
        shoff = struct.unpack_from('<Q', data, 40)[0]
        count = struct.unpack_from('<H', data, 60)[0]
        for i in range(count):
            offset, size = struct.unpack_from('<QQ', data, shoff + i*64 + 24)
            if data[offset:offset+size] == note():
                struct.pack_into('<I', data, shoff+i*64+4, 7)
        (self.root / 'two-ids').write_bytes(data)
        with self.assertRaisesRegex(ValueError, 'found 2'): B.elf_build_id(self.root / 'two-ids')


if __name__ == '__main__': unittest.main()
