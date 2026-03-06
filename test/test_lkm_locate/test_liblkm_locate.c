// Simple user-space harness to call functions from liblkm_locate.so.

// LD_LIBRARY_PATH=../../make_dll  ./test_liblkm_locate
#include <stdio.h>
#include <stdlib.h>

// Symbols exported by liblkm_locate.so
int lkm_locate_test_all_pseudo_got(int x);

static void run_case(int x) {
    int result = lkm_locate_test_all_pseudo_got(x);
    printf("input=%d result=0x%x\n", x, result);
}

int main(void) {
    run_case(1);
    run_case(42);
    run_case(7);
    return 0;
}
