# Change Log

Each change log must describe all modifications introduced in that step.

For every change log include:

- File modified
- Symbol changes
- Internal code modifications (if any)
- Reason for modification

# example:
## change log x
**Files modified:**
zlib_deflate.c
zlib_inflate.c
zlib.h

**Symbol changes:**
zlib_deflate -> mz_zlib_deflate
inflate_fast -> mz_inflate_fast

**Internal code modifications:**
None

**Reason:**
Global symbol namespace isolation for kernel module.
---

## change log 1

Initial import of kernel zlib source.

**Modifications:**
None

---

## change log 2
