#include "trace.h"
#define dlopen setup_dlopen
#define dlsym setup_dlsym
#define main original_benchmark_main
#include "../../test_lz4/src/lz4-bench.c"
#undef main
#undef dlopen
#undef dlsym
int main(int argc, char **argv) {
    setup_mark("process.main");
    if (argc != 5) die("usage: setup-lz4 LIBRARY MANIFEST BLOCK_BYTES ITERATIONS");
    int block = atoi(argv[3]), iterations = atoi(argv[4]);
    if ((block != 4096 && block != 65536 && block != 1048576) || iterations < 1)
        die("invalid setup workload");
    struct backend backend = {.name="selected", .path=argv[1], .kind=BACKEND_KERNEL};
    setup_mark("load.begin"); init_backend(&backend); setup_mark("load.end");
    setup_mark("input.begin");
    struct corpus corpus = load_corpus(argv[2]);
    struct chunk_set chunks = make_chunks(&corpus, block);
    unsigned char *compressed = xmalloc(chunks.storage_size), *decoded = xmalloc(corpus.size);
    setup_mark("input.end");
    setup_mark("task.begin");
    for (int i=0; i<iterations; ++i) {
        compress_corpus(&backend, &corpus, &chunks, compressed);
        decompress_corpus(&backend, &chunks, compressed, decoded);
        if (memcmp(decoded, corpus.data, corpus.size)) die("setup full corpus mismatch");
        if (i == 0) setup_mark("first.valid");
    }
    setup_mark("task.end");
    free(decoded); free(compressed); free(chunks.items); free(corpus.data); free(corpus.files);
    setup_mark("unload.begin"); destroy_backend(&backend); setup_mark("unload.end");
    printf("valid\tlz4\t%zu\t%zu\t%d\n", corpus.file_count, corpus.size, iterations);
    setup_flush(); return 0;
}
