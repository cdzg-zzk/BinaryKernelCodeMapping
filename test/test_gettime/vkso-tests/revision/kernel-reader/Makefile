obj-m += vkso_kernel_reader.o
# Keep test-only instrumentation out of the measurement loop.
CFLAGS_REMOVE_vkso_kernel_reader.o += $(CC_FLAGS_FTRACE)
