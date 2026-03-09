# Agent Rules

The following rules MUST be followed.

## Core Rules

1. NEVER modify algorithm logic.

2. ONLY the following changes are allowed:
   - Global symbol renaming
   - Header include adjustments
   - Module init/exit functions
   - EXPORT_SYMBOL declarations
   - Makefile creation

3. DO NOT refactor code.

4. DO NOT simplify code.

5. DO NOT remove existing code.

6. DO NOT change control flow.

7. DO NOT modify data structures.

## Symbol Renaming

Rename ONLY global symbols.

Prefix format:

mz_

Example:

zlib_deflate -> mz_zlib_deflate

Do NOT rename:

- static functions
- local variables
- macros unless they are exported symbols

## Kernel Compatibility

Use kernel APIs compatible with the current kernel version.

Allowed examples:

kmalloc  
kfree  

## Output Behavior

When task is complete:

Print only:

change log X

Do NOT output explanations.