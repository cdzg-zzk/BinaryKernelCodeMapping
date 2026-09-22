#include "trace.h"
#define dlopen setup_dlopen
#define dlsym setup_dlsym
#define main original_benchmark_main
#include "../../test_BCH/src/bch_bench.c"
#undef main
#undef dlopen
#undef dlsym
int main(int argc, char **argv) {
    setup_mark("process.main");
    if (argc != 4) die("usage: setup-bch LIBRARY native|kernel-vkso ITERATIONS");
    int iterations=atoi(argv[3]);
    if (iterations<1 || (strcmp(argv[2],"native") && strcmp(argv[2],"kernel-vkso"))) die("invalid setup workload");
    struct backend backend={.name=argv[2],.path=argv[1]};
    setup_mark("load.begin"); load_backend(&backend); setup_mark("load.end");
    setup_mark("task.begin");
    /* One complete task initializes, encodes, corrupts, decodes and validates
       both original geometries, then frees their controls. No parity shortcut. */
    for (int iteration=0; iteration<iterations; ++iteration) {
        for (int c=0; c<2; ++c) {
            struct bench_case test={.m=13,.t=c?8:4,.len=512};
            void *control=new_control(&backend,test.m,test.t);
            struct bch_public *pub=control;
            test.ecc_bits=pub->ecc_bits; test.ecc_bytes=pub->ecc_bytes;
            test.codeword=xcalloc((size_t)test.len+test.ecc_bytes,1);
            uint64_t seed=UINT64_C(0xb4c00000)+c;
            for (int i=0; i<test.len; ++i) test.codeword[i]=(uint8_t)prng_next(&seed);
            backend.encode(control,test.codeword,test.len,test.codeword+test.len);
            unsigned int vector[MAX_T];
            for (int errors=0; errors<=test.t; ++errors) {
                generate_error_vector(vector,errors,8U*test.len+test.ecc_bits,
                    UINT64_C(0x63c5a17e9b)^((uint64_t)c<<48)^(uint64_t)errors);
                struct op_context context={.backend=&backend,.control=control,.test=&test,
                    .mode=MODE_DECODE_FULL,.errors=errors};
                prepare_decode_context(&context,vector); verify_decode(&context,vector);
                free_decode_context(&context);
            }
            free(test.codeword); backend.free_control(control);
        }
        if (!iteration) setup_mark("first.valid");
    }
    setup_mark("task.end");
    setup_mark("unload.begin"); dlclose(backend.handle); setup_mark("unload.end");
    printf("valid\tbch\t2\t1024\t%d\n",iterations); setup_flush(); return 0;
}
