// Simple user-space harness to call functions from liblkm_locate.so.
#include <stdio.h>
#include <stdlib.h>

// Symbols exported by liblkm_locate.so
int lkm_locate_local_add(int x);
int lkm_locate_test_pseudo_got(int x);

static void run_case(int x) {
    int add = lkm_locate_local_add(x);
    int pseudo = lkm_locate_test_pseudo_got(x);
    printf("input=%d local_add=0x%x pseudo_got=0x%x\n", x, add, pseudo);
}

int main(void) {
    run_case(1);
    run_case(42);
    run_case(-7);
    return 0;
}
