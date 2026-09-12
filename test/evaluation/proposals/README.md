# Unapplied analyzer performance proposal

`checker-symbol-cache.patch` changes only `ELFObj` in
`kernel_cgd/function_checker/functions_checker.py`. It builds function ranges
once while reading the existing symbol table, preserves their original order
within each section, and caches `(section, offset)` lookups. It preserves the
existing first-match rule for aliases/overlap, zero-sized functions and missing
targets. No static acceptance, Shim, instrumentation, relocation, control-flow,
runtime-address or export rule is changed.

The current resolver reparses the ELF symbol table on every direct-target
lookup. During the live `hex_dump_to_buffer` inspection, the traversal through
formatting helpers continued for more than 30 minutes. The proposal addresses
that repeated parsing; it does not truncate the closure or replace the API with
a narrower branch.

The patch has **not** been applied to the checker. `git apply --check` succeeds.
An isolated copy passed 40 queries on an assembled fixture with overlapping
symbols, aliases, a zero-sized function, a data symbol and missing sections;
repeated lookups also agree. Nine queries against the actual 5.15.0-119 image
match the unchanged resolver, including interior offsets and a missing section.
Their observed lookup times were 35.647 s versus 0.051 s after object creation.
These are diagnostic timings for those queries, not campaign results or a
general speedup estimate. See `checker-symbol-cache-validation.json`.

Application and a fresh complete eight-case inspection await the user's answer
because this touches the foundational analyzer. The current unmodified checker
continues running. If approved, preserve its completed/partial records, apply
the patch, compare the three already-complete manifests, and inspect all eight
fixed candidates into a fresh directory. No Clocktime experiment is restarted.
