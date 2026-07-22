# Clean VKSO working tree

## Purpose

This is the native x86-64 VKSO implementation tree.  It was copied from
`../linux-5.15.198-no-vdso` after the x86 vDSO/VVAR path and the old time
namespace VVAR coupling had been removed.  The source tree is built with an
external `O=` directory; generated kernel files do not belong here.

The unmodified comparison kernel remains the raw Linux 5.15.198 source.  The
no-vDSO tree is an immutable intermediate baseline and must not receive VKSO
changes.

## Git policy

The project-root Git repository tracks only the VKSO integration surface of
this kernel tree, not the complete Linux source.  Development takes place on
the root repository's `vkso-implementation` branch.  The complete directory
is ignored and selected kernel files are force-added to the project repository.

Before editing an existing but untracked kernel file:

1. From the project root, add its unmodified no-vDSO version with
   `git add -f test/test_gettime/linux-5.15.198-vkso/path/to/file`.
2. Commit it as an additional baseline file.
3. Make the VKSO change in a later commit.

All new VKSO sources, tests, configuration fragments and documentation must be
added with `git add -f`.  `test/test_gettime/.gitignore` hides the rest of the
kernel tree so that only the maintained integration surface enters commits.

## Supported configuration

The experiment targets native x86-64 only.  IA32, x32, SGX vDSO and
checkpoint/restore vDSO remapping are outside scope and disabled in both raw
and VKSO kernels.  Legacy vsyscall is independent and is kept identical in
both kernels.

The native API target is:

- `__vkso_clock_gettime`
- `__vkso_clock_getres`
- `__vkso_gettimeofday`
- `__vkso_time`
- `__vkso_getcpu`

Functionality must be at least the native x86-64 raw-vDSO functionality under
the same configuration.  QEMU is used only for correctness; it is not a
performance environment.

## Build convention

Use a clean external build directory, for example:

```sh
make O=/tmp/vkso-kernel-build no_vdso_defconfig
scripts/kconfig/merge_config.sh -m -O /tmp/vkso-kernel-build \
    /tmp/vkso-kernel-build/.config vkso-qemu.config
make O=/tmp/vkso-kernel-build olddefconfig
make O=/tmp/vkso-kernel-build -j8 bzImage
```

The final raw and VKSO configurations must be compared after `olddefconfig`;
only VKSO-specific symbols may differ.
