#!/usr/bin/env python3
"""Exercise overlapping matches and dictionary wrap through the public decoder."""
import argparse
import ctypes as C
import json
import lzma
from pathlib import Path
import random


class Buffer(C.Structure):
    _fields_ = [('input', C.c_void_p), ('in_pos', C.c_size_t),
                ('in_size', C.c_size_t), ('output', C.c_void_p),
                ('out_pos', C.c_size_t), ('out_size', C.c_size_t)]


def check(library, streaming=False):
    lib = C.CDLL(str(Path(library).resolve()))
    lib.xz_dec_init.argtypes = [C.c_int, C.c_uint32]
    lib.xz_dec_init.restype = C.c_void_p
    lib.xz_dec_run.argtypes = [C.c_void_p, C.POINTER(Buffer)]
    lib.xz_dec_run.restype = C.c_int
    lib.xz_dec_end.argtypes = [C.c_void_p]
    lib.xz_crc32_init()
    rng = random.Random(63)
    block = bytes(rng.randrange(256) for _ in range(4096))
    inputs = {'distance-one': b'A' * 65537,
              'distance-seven': b'abcdefg' * 10001,
              'dictionary-wrap': block * 17 + block[:513]}
    rows = []
    for name, plain in inputs.items():
        compressed = lzma.compress(plain, check=lzma.CHECK_CRC32,
            filters=[{'id': lzma.FILTER_LZMA2, 'dict_size': 4096}])
        source = C.create_string_buffer(compressed)
        for mode in ((0, 2) if streaming else (0,)):
            decoder = lib.xz_dec_init(mode, 4096)
            assert decoder, 'decoder allocation failed'
            result = bytearray()
            consumed = 0
            calls = 0
            try:
                while True:
                    size = len(plain) if mode == 0 else 257
                    target = C.create_string_buffer(size)
                    buf = Buffer(C.addressof(source), consumed, len(compressed),
                                 C.addressof(target), 0, size)
                    status = lib.xz_dec_run(decoder, C.byref(buf))
                    calls += 1
                    result.extend(target.raw[:buf.out_pos])
                    assert status in (0, 1), (name, mode, status)
                    assert buf.in_pos > consumed or buf.out_pos or status == 1
                    consumed = buf.in_pos
                    if status == 1:
                        break
                    assert calls < len(plain) + 1
                assert consumed == len(compressed) and result == plain, (name, mode)
            finally:
                lib.xz_dec_end(decoder)
            rows.append(dict(input=name, mode=mode, bytes=len(plain), calls=calls,
                             output_matches=True))
    return dict(status='pass', scope='functional only; not performance evidence',
                library=str(Path(library).resolve()), rows=rows)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('library', type=Path)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--streaming', action='store_true',
                   help='library must be built with XZ_DEC_DYNALLOC')
    args = p.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(check(args.library, args.streaming), indent=2) + '\n')
