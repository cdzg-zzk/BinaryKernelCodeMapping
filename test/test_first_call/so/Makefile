obj-m += zzk_xxh32_lkm.o
zzk_xxh32_lkm-objs := zzk_xxh32_module.o zzk_xxh32_kernel.o
CFLAGS_zzk_xxh32_module.o := -mfunction-return=keep
OBJECT_FILES_NON_STANDARD_zzk_xxh32_module.o := y

all: module user

module: zzk_xxh32_module.c zzk_xxh32_kernel.S
	$(MAKE) -C /lib/modules/$(shell uname -r)/build M=$(PWD) modules

user: clone_xxh32_user.S
	gcc -fPIC -O2 -c clone_xxh32_user.S -o clone_xxh32_user.o
	ld -shared --build-id=none --hash-style=gnu -z norelro -T clone_xxh32_min.ld -soname libclone_xxh32.so -o libclone_xxh32.so clone_xxh32_user.o
	strip --strip-unneeded libclone_xxh32.so

clean:
	$(MAKE) -C /lib/modules/$(shell uname -r)/build M=$(PWD) clean
	rm -f libclone_xxh32.so clone_xxh32_user.o
