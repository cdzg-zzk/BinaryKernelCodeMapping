# SPDX-License-Identifier: GPL-2.0
obj-y += time.o timer.o hrtimer.o
obj-$(CONFIG_VKSO_TIME) += vkso_time_core.o vkso_time_cycles.o vkso_time.o
obj-$(CONFIG_VKSO_TIME_TEST) += vkso_time_test.o

# These objects are mapped into user space as well as called by the kernel.
# Do not let the compiler add instrumentation that requires kernel-only state.
CFLAGS_vkso_time_core.o := -fno-stack-protector
CFLAGS_REMOVE_vkso_time_core.o := $(CC_FLAGS_FTRACE)
GCOV_PROFILE_vkso_time_core.o := n
KCOV_INSTRUMENT_vkso_time_core.o := n
KASAN_SANITIZE_vkso_time_core.o := n
KCSAN_SANITIZE_vkso_time_core.o := n
UBSAN_SANITIZE_vkso_time_core.o := n
CFLAGS_vkso_time_cycles.o := -fno-stack-protector
CFLAGS_REMOVE_vkso_time_cycles.o := $(CC_FLAGS_FTRACE)
GCOV_PROFILE_vkso_time_cycles.o := n
KCOV_INSTRUMENT_vkso_time_cycles.o := n
KASAN_SANITIZE_vkso_time_cycles.o := n
KCSAN_SANITIZE_vkso_time_cycles.o := n
UBSAN_SANITIZE_vkso_time_cycles.o := n
CFLAGS_vkso_time_test.o := -fno-stack-protector
CFLAGS_REMOVE_vkso_time_test.o := $(CC_FLAGS_FTRACE)
GCOV_PROFILE_vkso_time_test.o := n
KCOV_INSTRUMENT_vkso_time_test.o := n
KASAN_SANITIZE_vkso_time_test.o := n
KCSAN_SANITIZE_vkso_time_test.o := n
UBSAN_SANITIZE_vkso_time_test.o := n
obj-y += timekeeping.o ntp.o clocksource.o jiffies.o timer_list.o
obj-y += timeconv.o timecounter.o alarmtimer.o

ifeq ($(CONFIG_POSIX_TIMERS),y)
 obj-y += posix-timers.o posix-cpu-timers.o posix-clock.o itimer.o
else
 obj-y += posix-stubs.o
endif

obj-$(CONFIG_GENERIC_CLOCKEVENTS)		+= clockevents.o tick-common.o
ifeq ($(CONFIG_GENERIC_CLOCKEVENTS_BROADCAST),y)
 obj-y						+= tick-broadcast.o
 obj-$(CONFIG_TICK_ONESHOT)			+= tick-broadcast-hrtimer.o
endif
obj-$(CONFIG_GENERIC_SCHED_CLOCK)		+= sched_clock.o
obj-$(CONFIG_TICK_ONESHOT)			+= tick-oneshot.o tick-sched.o
obj-$(CONFIG_LEGACY_TIMER_TICK)			+= tick-legacy.o
obj-$(CONFIG_DEBUG_FS)				+= timekeeping_debug.o
obj-$(CONFIG_TEST_UDELAY)			+= test_udelay.o
obj-$(CONFIG_TIME_NS)				+= namespace.o
obj-$(CONFIG_TEST_CLOCKSOURCE_WATCHDOG)		+= clocksource-wdtest.o
obj-$(CONFIG_TIME_KUNIT_TEST)			+= time_test.o
