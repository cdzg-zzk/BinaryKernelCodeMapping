# Section 6.1 — Page Grafting Overhead

- [Benchmark and protocol](../test_first_call/matrix_bench/README.md)
- [Identical-instruction XXH32 owner](../test_first_call/so/README.md)
- [Execution evidence](../evaluation/first-touch-evidence.md)

This section compares Native and VKSO under hot, PTE-cold and post-drop states.
Its same-instruction control isolates page backing/mapping behavior. The
algorithm exports and their compiler/source adaptations belong to section 6.3.
