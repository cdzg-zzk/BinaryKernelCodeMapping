#include "trace.h"
#define dlopen setup_dlopen
#define dlsym setup_dlsym
#define main original_benchmark_main
#include "../../test_xz/src/xz-bench.c"
#undef main
#undef dlopen
#undef dlsym
int main(int argc, char **argv) {
    setup_mark("process.main");
    if (argc < 8 || (argc-5)%3) die("usage: setup-xz LIBRARY PREFIX ITERATIONS -- LABEL PLAIN XZ [...]");
    int count=(argc-5)/3, iterations=atoi(argv[3]);
    if (iterations < 1 || strcmp(argv[4], "--")) die("invalid setup workload");
    struct backend backend={.name="selected"};
    setup_mark("load.begin"); load_backend(&backend, argv[1], argv[2]); setup_mark("load.end");
    setup_mark("input.begin");
    struct input *inputs=calloc(count, sizeof(*inputs));
    uint8_t **output=calloc(count, sizeof(*output));
    if (!inputs || !output) die("setup allocation failed");
    size_t total=0;
    for (int i=0; i<count; ++i) {
        inputs[i].label=argv[5+3*i];
        inputs[i].plain=read_file(argv[6+3*i], &inputs[i].plain_size);
        inputs[i].compressed=read_file(argv[7+3*i], &inputs[i].compressed_size);
        if (!inputs[i].plain || !inputs[i].compressed) die("setup input failed");
        output[i]=malloc(inputs[i].plain_size+128);
        if (!output[i]) die("setup output failed");
        memset(output[i], 0xA5, inputs[i].plain_size+128); total+=inputs[i].plain_size;
    }
    setup_mark("input.end");
    setup_mark("task.begin");
    for (int iteration=0; iteration<iterations; ++iteration) {
        for (int i=0; i<count; ++i) {
            struct xz_dec *decoder=backend.dec_init(XZ_SINGLE, 0);
            if (!decoder) die("setup decoder init failed");
            decode_once(&backend, decoder, &inputs[i], output[i]+64, 0);
            if (memcmp(output[i]+64, inputs[i].plain, inputs[i].plain_size) ||
                !guard_is_intact(output[i],64) || !guard_is_intact(output[i]+64+inputs[i].plain_size,64))
                die("setup full XZ output/guard mismatch");
            backend.dec_end(decoder);
        }
        if (!iteration) setup_mark("first.valid");
    }
    setup_mark("task.end");
    for (int i=0; i<count; ++i) { free(output[i]); free(inputs[i].plain); free(inputs[i].compressed); }
    free(output); free(inputs);
    setup_mark("unload.begin"); dlclose(backend.handle); setup_mark("unload.end");
    printf("valid\txz\t%d\t%zu\t%d\n",count,total,iterations);
    setup_flush(); return 0;
}
