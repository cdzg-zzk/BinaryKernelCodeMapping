# Reproducible paper figures

Regenerate every checked SVG from the repository root:

```sh
python3 paper/paper_content/figures/generate_figures.py
```

The generator uses only the Python standard library. It reads the final CSV
artifacts for first-touch, PGOT, LZ4, BCH, and XZ directly. Clocktime aggregates
come from `VKSO_READ_UPDATE性能报告_20260801.md`; the script checks the report's
tagged values before writing those figures. Architecture and mechanism diagrams
are deterministic vector drawings produced by the same script.

The XZ figure reads `test/test_xz/results/formal-20260806/raw.csv`. That formal
artifact contains seven pinned-CPU outer runs for each of three inputs and has
passed the DSO, relocation, output, and guard-region checks described in
`test/test_xz/README.md`.
