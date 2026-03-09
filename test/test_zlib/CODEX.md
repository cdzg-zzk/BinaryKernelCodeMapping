This repository is controlled by an AI coding agent.
Follow AGENT_RULES.md strictly.
 &
Add change to CHANGELOG.md
# zlib Kernel Module Refactor

Follow this document strictly.  
Do not deviate from constraints.

## Goal
Extract the Linux kernel zlib implementation and package it as an independent Loadable Kernel Module (LKM).

The compression and decompression behavior MUST remain identical to the original kernel zlib.

## Constraints
See AGENT_RULES.md

## Input
Linux kernel zlib source files, typically located in:

lib/zlib_*

Files include:
- .c
- .h

## Output
A standalone kernel module source tree containing:

- Modified zlib source files
- Makefile for building `.ko`
- Module init / exit functions
- Exported symbols if needed

The module must compile against kernel headers.

## Symbol Rename Rule
All global symbols must be renamed with prefix:

mz_

Example:

zlib_deflate -> mz_zlib_deflate  
inflate_fast -> mz_inflate_fast  

Static functions and local variables MUST NOT be renamed.

## Output Rule
Do NOT explain modifications in terminal output.

Only print:

change log X

Where X is the latest change log number.

## Change Log
See CHANGELOG.md