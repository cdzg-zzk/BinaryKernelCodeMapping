// SPDX-License-Identifier: GPL-2.0

#include <linux/device.h>
#include <linux/fs.h>
#include <linux/ktime.h>
#include <linux/module.h>
#include <linux/posix-clock.h>

#define VKSO_M09_CLOCK_NAME "vkso-m09-clock"

struct vkso_m09_clock {
	struct posix_clock clock;
	struct device device;
	dev_t devt;
};

static struct vkso_m09_clock test_clock;
static struct class *test_class;

static int
vkso_m09_clock_gettime(struct posix_clock *clock, struct timespec64 *value)
{
	(void)clock;
	ktime_get_real_ts64(value);
	return 0;
}

static int
vkso_m09_clock_getres(struct posix_clock *clock, struct timespec64 *value)
{
	(void)clock;
	value->tv_sec = 0;
	value->tv_nsec = 1;
	return 0;
}

static void vkso_m09_clock_release(struct device *device)
{
	(void)device;
}

static int __init vkso_m09_clock_init(void)
{
	int error;

	error = alloc_chrdev_region(&test_clock.devt, 0, 1,
				    VKSO_M09_CLOCK_NAME);
	if (error)
		return error;

	test_class = class_create(THIS_MODULE, VKSO_M09_CLOCK_NAME);
	if (IS_ERR(test_class)) {
		error = PTR_ERR(test_class);
		goto unregister_region;
	}

	test_clock.clock.ops.owner = THIS_MODULE;
	test_clock.clock.ops.clock_gettime = vkso_m09_clock_gettime;
	test_clock.clock.ops.clock_getres = vkso_m09_clock_getres;

	device_initialize(&test_clock.device);
	test_clock.device.class = test_class;
	test_clock.device.devt = test_clock.devt;
	test_clock.device.release = vkso_m09_clock_release;
	error = dev_set_name(&test_clock.device, VKSO_M09_CLOCK_NAME);
	if (error)
		goto put_device;

	error = posix_clock_register(&test_clock.clock, &test_clock.device);
	if (error)
		goto put_device;

	pr_info("VKSO M09 dynamic clock registered\n");
	return 0;

put_device:
	put_device(&test_clock.device);
	class_destroy(test_class);
unregister_region:
	unregister_chrdev_region(test_clock.devt, 1);
	return error;
}

static void __exit vkso_m09_clock_exit(void)
{
	posix_clock_unregister(&test_clock.clock);
	class_destroy(test_class);
	unregister_chrdev_region(test_clock.devt, 1);
}

module_init(vkso_m09_clock_init);
module_exit(vkso_m09_clock_exit);

MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("VKSO M09 dynamic POSIX clock validation device");
