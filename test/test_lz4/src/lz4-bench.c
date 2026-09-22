#define _GNU_SOURCE

#include <dlfcn.h>
#include <errno.h>
#include <fcntl.h>
#include <inttypes.h>
#include <limits.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <time.h>
#include <unistd.h>

#define ARRAY_SIZE(a) (sizeof(a) / sizeof((a)[0]))
#define KERNEL_WORKMEM_SIZE (64u * 1024u)

typedef int (*user_compress_fn)(void *, const char *, char *, int, int, int);
typedef int (*kernel_compress_fn)(const char *, char *, int, int, void *);
typedef int (*decompress_fn)(const char *, char *, int, int);
typedef int (*state_size_fn)(void);

enum backend_kind {
  BACKEND_USER,
  BACKEND_KERNEL,
};

struct backend {
  const char *name;
  const char *path;
  enum backend_kind kind;
  void *handle;
  user_compress_fn user_compress;
  kernel_compress_fn kernel_compress;
  decompress_fn decompress;
  void *workmem;
  size_t workmem_size;
};

struct file_span {
  size_t offset;
  size_t size;
};

struct corpus {
  unsigned char *data;
  size_t size;
  struct file_span *files;
  size_t file_count;
};

struct chunk {
  size_t input_offset;
  int input_size;
  size_t output_offset;
  int output_capacity;
  int compressed_size;
};

struct chunk_set {
  struct chunk *items;
  size_t count;
  size_t storage_size;
};

struct options {
  const char *default_library;
  const char *nosimd_library;
  const char *kernel_user_native_library;
  const char *kernel_user_nosimd_library;
  const char *kernel_user_libc_library;
  const char *kernel_library;
  const char *manifest;
  const char *block_sizes;
  int correctness_only;
  int repeats;
  int warmups;
  int run_id;
  int order;
};

static volatile uint64_t result_sink;

static void
die(const char *message)
{
  fprintf(stderr, "%s\n", message);
  exit(EXIT_FAILURE);
}

static void
die_errno(const char *message)
{
  perror(message);
  exit(EXIT_FAILURE);
}

static void *
xmalloc(size_t size)
{
  void *result = malloc(size != 0 ? size : 1);
  if (result == NULL)
    die_errno("malloc");
  return result;
}

static void *
xcalloc(size_t count, size_t size)
{
  void *result = calloc(count != 0 ? count : 1, size != 0 ? size : 1);
  if (result == NULL)
    die_errno("calloc");
  return result;
}

static void *
xrealloc(void *pointer, size_t size)
{
  void *result = realloc(pointer, size != 0 ? size : 1);
  if (result == NULL)
    die_errno("realloc");
  return result;
}

static uint64_t
nanoseconds(const struct timespec *start, const struct timespec *end)
{
  return (uint64_t)(end->tv_sec - start->tv_sec) * UINT64_C(1000000000)
         + (uint64_t)(end->tv_nsec - start->tv_nsec);
}

static inline uint64_t
tsc_start(void)
{
  unsigned int low, high;
  __asm__ volatile("lfence\n\trdtsc" : "=a"(low), "=d"(high) :: "memory");
  return ((uint64_t)high << 32) | low;
}

static inline uint64_t
tsc_stop(void)
{
  unsigned int low, high, auxiliary;
  __asm__ volatile("rdtscp\n\tlfence"
                   : "=a"(low), "=d"(high), "=c"(auxiliary)
                   :: "memory");
  (void)auxiliary;
  return ((uint64_t)high << 32) | low;
}

static int
compress_bound(int input_size)
{
  if (input_size < 0 || input_size > 0x7e000000)
    return 0;
  return input_size + input_size / 255 + 16;
}

static void
load_symbol(void *handle, const char *name, void *target, size_t target_size)
{
  void *symbol;
  const char *error;

  dlerror();
  symbol = dlsym(handle, name);
  error = dlerror();
  if (symbol == NULL || error != NULL) {
    fprintf(stderr, "dlsym(%s): %s\n", name,
            error != NULL ? error : "symbol address is null");
    exit(EXIT_FAILURE);
  }
  if (target_size != sizeof(symbol))
    die("function pointer size is not compatible with dlsym");
  memcpy(target, &symbol, sizeof(symbol));
}

static void
init_backend(struct backend *backend)
{
  state_size_fn get_state_size = NULL;
  int allocation_error;

  backend->handle = dlopen(backend->path, RTLD_NOW | RTLD_LOCAL);
  if (backend->handle == NULL) {
    fprintf(stderr, "dlopen(%s): %s\n", backend->path, dlerror());
    exit(EXIT_FAILURE);
  }

  if (backend->kind == BACKEND_USER) {
    load_symbol(backend->handle, "LZ4_decompress_safe",
                &backend->decompress, sizeof(backend->decompress));
    load_symbol(backend->handle, "LZ4_compress_fast_extState",
                &backend->user_compress, sizeof(backend->user_compress));
    load_symbol(backend->handle, "LZ4_sizeofState", &get_state_size,
                sizeof(get_state_size));
    backend->workmem_size = (size_t)get_state_size();
  } else {
    load_symbol(backend->handle, "vkso_LZ4_decompress_safe",
                &backend->decompress, sizeof(backend->decompress));
    load_symbol(backend->handle, "vkso_LZ4_compress_default",
                &backend->kernel_compress, sizeof(backend->kernel_compress));
    backend->workmem_size = KERNEL_WORKMEM_SIZE;
  }

  allocation_error = posix_memalign(&backend->workmem, 64,
                                    backend->workmem_size);
  if (allocation_error != 0) {
    errno = allocation_error;
    die_errno("posix_memalign LZ4 state");
  }
  memset(backend->workmem, 0, backend->workmem_size);
}

static int
backend_compress(struct backend *backend, const unsigned char *source,
                 unsigned char *destination, int source_size,
                 int destination_capacity)
{
  if (backend->kind == BACKEND_KERNEL)
    return backend->kernel_compress((const char *)source,
                                    (char *)destination, source_size,
                                    destination_capacity, backend->workmem);
  return backend->user_compress(backend->workmem, (const char *)source,
                                (char *)destination, source_size,
                                destination_capacity, 1);
}

static int
backend_decompress(struct backend *backend, const unsigned char *source,
                   unsigned char *destination, int compressed_size,
                   int destination_capacity)
{
  return backend->decompress((const char *)source, (char *)destination,
                             compressed_size, destination_capacity);
}

static void
destroy_backend(struct backend *backend)
{
  free(backend->workmem);
  if (backend->handle != NULL)
    dlclose(backend->handle);
}

static void
fill_test_data(unsigned char *data, size_t size, unsigned int variant)
{
  uint32_t state = UINT32_C(0x9e3779b9) ^ variant;
  size_t index;

  for (index = 0; index < size; ++index) {
    if ((variant & 1u) == 0)
      data[index] = (unsigned char)("kernel-lz4-correctness"[index % 22]);
    else {
      state ^= state << 13;
      state ^= state >> 17;
      state ^= state << 5;
      data[index] = (unsigned char)state;
    }
  }
}

static void
run_correctness(struct backend *backends, size_t backend_count)
{
  static const size_t sizes[] = {
    0, 1, 15, 16, 31, 64, 255, 256, 4095, 4096, 65535, 65536
  };
  size_t size_index, compressor_index, decompressor_index;
  int trace = getenv("VKSO_TRACE_CORRECTNESS") != NULL;

  for (size_index = 0; size_index < ARRAY_SIZE(sizes); ++size_index) {
    size_t size = sizes[size_index];
    int capacity = compress_bound((int)size);
    unsigned char *source = xmalloc(size);
    unsigned char *compressed = xmalloc((size_t)capacity + 32);
    unsigned char *decoded = xmalloc(size + 32);

    fill_test_data(source, size, (unsigned int)size_index);
    for (compressor_index = 0; compressor_index < backend_count;
         ++compressor_index) {
      int compressed_size;
      if (trace) {
        fprintf(stderr, "correctness: compress=%s size=%zu\n",
                backends[compressor_index].name, size);
        fflush(stderr);
      }
      memset(compressed, 0xa5, (size_t)capacity + 32);
      compressed_size = backend_compress(&backends[compressor_index], source,
                                         compressed, (int)size, capacity);
      if (compressed_size <= 0 || compressed_size > capacity) {
        fprintf(stderr, "%s compression failed for size=%zu: %d\n",
                backends[compressor_index].name, size, compressed_size);
        exit(EXIT_FAILURE);
      }
      for (size_t guard = (size_t)capacity;
           guard < (size_t)capacity + 32; ++guard) {
        if (compressed[guard] != 0xa5)
          die("compression overwrote its destination guard");
      }

      for (decompressor_index = 0; decompressor_index < backend_count;
           ++decompressor_index) {
        int decoded_size;
        if (trace) {
          fprintf(stderr, "correctness: decompress=%s from=%s size=%zu\n",
                  backends[decompressor_index].name,
                  backends[compressor_index].name, size);
          fflush(stderr);
        }
        memset(decoded, 0x5a, size + 32);
        decoded_size = backend_decompress(&backends[decompressor_index],
                                          compressed, decoded,
                                          compressed_size, (int)size);
        if (decoded_size != (int)size
            || (size != 0 && memcmp(source, decoded, size) != 0)) {
          fprintf(stderr,
                  "cross-decode failed: compressor=%s decompressor=%s "
                  "size=%zu decoded=%d\n",
                  backends[compressor_index].name,
                  backends[decompressor_index].name, size, decoded_size);
          exit(EXIT_FAILURE);
        }
        for (size_t guard = size; guard < size + 32; ++guard) {
          if (decoded[guard] != 0x5a)
            die("decompression overwrote its destination guard");
        }
      }
    }
    free(decoded);
    free(compressed);
    free(source);
  }

  printf("cross-backend correctness: PASS (%zu compressors x %zu "
         "decompressors x %zu sizes)\n",
         backend_count, backend_count, ARRAY_SIZE(sizes));
}

static char *
manifest_base_directory(const char *manifest)
{
  const char *slash = strrchr(manifest, '/');
  size_t length = slash != NULL ? (size_t)(slash - manifest) : 1;
  char *result;

  if (slash == NULL)
    return strdup(".");
  if (length == 0)
    length = 1;
  result = xmalloc(length + 1);
  memcpy(result, manifest, length);
  result[length] = '\0';
  return result;
}

static void
append_file(struct corpus *corpus, const char *path)
{
  int descriptor = open(path, O_RDONLY | O_CLOEXEC);
  struct stat status;
  struct file_span span;
  size_t offset;

  if (descriptor < 0) {
    fprintf(stderr, "open corpus file %s: %s\n", path, strerror(errno));
    exit(EXIT_FAILURE);
  }
  if (fstat(descriptor, &status) != 0)
    die_errno("fstat corpus file");
  if (!S_ISREG(status.st_mode) || status.st_size <= 0) {
    close(descriptor);
    return;
  }
  if ((uintmax_t)status.st_size > SIZE_MAX - corpus->size)
    die("corpus is too large");

  span.offset = corpus->size;
  span.size = (size_t)status.st_size;
  corpus->data = xrealloc(corpus->data, corpus->size + span.size);
  offset = 0;
  while (offset < span.size) {
    ssize_t count = read(descriptor, corpus->data + span.offset + offset,
                         span.size - offset);
    if (count < 0) {
      if (errno == EINTR)
        continue;
      die_errno("read corpus file");
    }
    if (count == 0)
      die("short read from corpus file");
    offset += (size_t)count;
  }
  close(descriptor);

  corpus->files = xrealloc(corpus->files,
                           (corpus->file_count + 1) * sizeof(*corpus->files));
  corpus->files[corpus->file_count++] = span;
  corpus->size += span.size;
}

static struct corpus
load_corpus(const char *manifest)
{
  struct corpus corpus = {0};
  FILE *stream = fopen(manifest, "r");
  char *base = manifest_base_directory(manifest);
  char *line = NULL;
  size_t line_capacity = 0;

  if (stream == NULL)
    die_errno("open corpus manifest");
  while (getline(&line, &line_capacity, stream) >= 0) {
    char path[PATH_MAX];
    size_t length = strcspn(line, "\r\n");
    line[length] = '\0';
    if (line[0] == '\0' || line[0] == '#')
      continue;
    if (line[0] == '/') {
      if (snprintf(path, sizeof(path), "%s", line) >= (int)sizeof(path))
        die("corpus path is too long");
    } else if (snprintf(path, sizeof(path), "%s/%s", base, line)
               >= (int)sizeof(path)) {
      die("corpus path is too long");
    }
    append_file(&corpus, path);
  }
  free(line);
  free(base);
  fclose(stream);
  if (corpus.file_count == 0 || corpus.size == 0)
    die("corpus manifest did not contain non-empty regular files");
  return corpus;
}

static struct chunk_set
make_chunks(const struct corpus *corpus, int block_size)
{
  struct chunk_set set = {0};
  size_t file_index, chunk_index = 0;

  for (file_index = 0; file_index < corpus->file_count; ++file_index)
    set.count += (corpus->files[file_index].size + (size_t)block_size - 1)
                 / (size_t)block_size;
  set.items = xcalloc(set.count, sizeof(*set.items));

  for (file_index = 0; file_index < corpus->file_count; ++file_index) {
    const struct file_span *file = &corpus->files[file_index];
    size_t consumed = 0;
    while (consumed < file->size) {
      struct chunk *chunk = &set.items[chunk_index++];
      size_t remaining = file->size - consumed;
      size_t size = remaining < (size_t)block_size ? remaining
                                                   : (size_t)block_size;
      int capacity = compress_bound((int)size);
      if (capacity <= 0 || set.storage_size > SIZE_MAX - (size_t)capacity)
        die("invalid LZ4 chunk capacity");
      chunk->input_offset = file->offset + consumed;
      chunk->input_size = (int)size;
      chunk->output_offset = set.storage_size;
      chunk->output_capacity = capacity;
      set.storage_size += (size_t)capacity;
      consumed += size;
    }
  }
  return set;
}

static size_t
compress_corpus(struct backend *backend, const struct corpus *corpus,
                struct chunk_set *chunks, unsigned char *storage)
{
  size_t total_output = 0;

  for (size_t index = 0; index < chunks->count; ++index) {
    struct chunk *chunk = &chunks->items[index];
    int result = backend_compress(
      backend, corpus->data + chunk->input_offset,
      storage + chunk->output_offset, chunk->input_size,
      chunk->output_capacity);
    if (result <= 0 || result > chunk->output_capacity)
      die("LZ4 compression failed during benchmark");
    chunk->compressed_size = result;
    total_output += (size_t)result;
  }
  result_sink += total_output;
  return total_output;
}

static size_t
decompress_corpus(struct backend *backend, const struct chunk_set *chunks,
                  const unsigned char *storage, unsigned char *decoded)
{
  size_t total_output = 0;

  for (size_t index = 0; index < chunks->count; ++index) {
    const struct chunk *chunk = &chunks->items[index];
    int result = backend_decompress(
      backend, storage + chunk->output_offset,
      decoded + chunk->input_offset, chunk->compressed_size,
      chunk->input_size);
    if (result != chunk->input_size)
      die("LZ4 decompression failed during benchmark");
    total_output += (size_t)result;
  }
  result_sink += total_output;
  return total_output;
}

static void
print_result(int run_id, const char *backend, const char *operation,
             int block_size, int repeat, size_t input_bytes,
             size_t compressed_bytes, uint64_t elapsed_ns,
             uint64_t elapsed_tsc)
{
  double mib_per_second = ((double)input_bytes * 1.0e9)
                          / ((double)elapsed_ns * 1024.0 * 1024.0);
  double ratio = (double)compressed_bytes / (double)input_bytes;
  printf("%d,%s,%s,%d,%d,%zu,%zu,%" PRIu64 ",%" PRIu64
         ",%.6f,%.9f,%.9f,%.9f\n",
         run_id, backend, operation, block_size, repeat, input_bytes,
         compressed_bytes, elapsed_ns, elapsed_tsc, mib_per_second,
         (double)elapsed_ns / (double)input_bytes,
         (double)elapsed_tsc / (double)input_bytes, ratio);
  fflush(stdout);
}

static void
benchmark_backend(struct backend *backend, const struct corpus *corpus,
                  int block_size, int warmups, int repeats, int run_id)
{
  struct chunk_set chunks = make_chunks(corpus, block_size);
  unsigned char *compressed = xmalloc(chunks.storage_size);
  unsigned char *decoded = xmalloc(corpus->size);
  size_t compressed_bytes = 0;

  for (int warmup = 0; warmup < warmups; ++warmup)
    compressed_bytes = compress_corpus(backend, corpus, &chunks, compressed);

  for (int repeat = 0; repeat < repeats; ++repeat) {
    struct timespec start_time, end_time;
    uint64_t start_tsc, end_tsc;
    if (clock_gettime(CLOCK_MONOTONIC_RAW, &start_time) != 0)
      die_errno("clock_gettime");
    start_tsc = tsc_start();
    compressed_bytes = compress_corpus(backend, corpus, &chunks, compressed);
    end_tsc = tsc_stop();
    if (clock_gettime(CLOCK_MONOTONIC_RAW, &end_time) != 0)
      die_errno("clock_gettime");
    print_result(run_id, backend->name, "compress", block_size, repeat,
                 corpus->size, compressed_bytes,
                 nanoseconds(&start_time, &end_time), end_tsc - start_tsc);
  }

  compressed_bytes = compress_corpus(backend, corpus, &chunks, compressed);
  (void)decompress_corpus(backend, &chunks, compressed, decoded);
  if (memcmp(decoded, corpus->data, corpus->size) != 0)
    die("validation decompression did not reproduce the corpus");
  for (int warmup = 0; warmup < warmups; ++warmup)
    (void)decompress_corpus(backend, &chunks, compressed, decoded);

  for (int repeat = 0; repeat < repeats; ++repeat) {
    struct timespec start_time, end_time;
    uint64_t start_tsc, end_tsc;
    if (clock_gettime(CLOCK_MONOTONIC_RAW, &start_time) != 0)
      die_errno("clock_gettime");
    start_tsc = tsc_start();
    (void)decompress_corpus(backend, &chunks, compressed, decoded);
    end_tsc = tsc_stop();
    if (clock_gettime(CLOCK_MONOTONIC_RAW, &end_time) != 0)
      die_errno("clock_gettime");
    if (memcmp(decoded, corpus->data, corpus->size) != 0)
      die("timed decompression did not reproduce the corpus");
    print_result(run_id, backend->name, "decompress", block_size, repeat,
                 corpus->size, compressed_bytes,
                 nanoseconds(&start_time, &end_time), end_tsc - start_tsc);
  }

  free(decoded);
  free(compressed);
  free(chunks.items);
}

static size_t
parse_block_sizes(const char *text, int **result)
{
  char *copy = strdup(text);
  char *save = NULL;
  char *token;
  int *values = NULL;
  size_t count = 0;

  if (copy == NULL)
    die_errno("strdup block sizes");
  for (token = strtok_r(copy, ",", &save); token != NULL;
       token = strtok_r(NULL, ",", &save)) {
    char *end = NULL;
    long value = strtol(token, &end, 10);
    if (*token == '\0' || *end != '\0' || value <= 0 || value > INT_MAX)
      die("invalid --block-sizes value");
    values = xrealloc(values, (count + 1) * sizeof(*values));
    values[count++] = (int)value;
  }
  free(copy);
  if (count == 0)
    die("--block-sizes is empty");
  *result = values;
  return count;
}

static int
parse_positive(const char *text, int allow_zero)
{
  char *end = NULL;
  long value = strtol(text, &end, 10);
  if (*text == '\0' || *end != '\0' || value < (allow_zero ? 0 : 1)
      || value > INT_MAX)
    die("invalid numeric option");
  return (int)value;
}

static struct options
parse_options(int argc, char **argv)
{
  struct options options = {
    .block_sizes = "4096,65536,1048576",
    .repeats = 5,
    .warmups = 1,
  };

  for (int index = 1; index < argc; ++index) {
    if (strcmp(argv[index], "--correctness") == 0)
      options.correctness_only = 1;
    else if (index + 1 >= argc)
      die("missing option argument");
    else if (strcmp(argv[index], "--user-default") == 0)
      options.default_library = argv[++index];
    else if (strcmp(argv[index], "--user-nosimd") == 0)
      options.nosimd_library = argv[++index];
    else if (strcmp(argv[index], "--kernel-user-native") == 0)
      options.kernel_user_native_library = argv[++index];
    else if (strcmp(argv[index], "--kernel-user-nosimd") == 0)
      options.kernel_user_nosimd_library = argv[++index];
    else if (strcmp(argv[index], "--kernel-user-libc") == 0)
      options.kernel_user_libc_library = argv[++index];
    else if (strcmp(argv[index], "--kernel") == 0)
      options.kernel_library = argv[++index];
    else if (strcmp(argv[index], "--manifest") == 0)
      options.manifest = argv[++index];
    else if (strcmp(argv[index], "--block-sizes") == 0)
      options.block_sizes = argv[++index];
    else if (strcmp(argv[index], "--repeats") == 0)
      options.repeats = parse_positive(argv[++index], 0);
    else if (strcmp(argv[index], "--warmups") == 0)
      options.warmups = parse_positive(argv[++index], 1);
    else if (strcmp(argv[index], "--run") == 0)
      options.run_id = parse_positive(argv[++index], 1);
    else if (strcmp(argv[index], "--order") == 0)
      options.order = parse_positive(argv[++index], 1);
    else
      die("unknown command-line option");
  }

  if (options.default_library == NULL || options.nosimd_library == NULL
      || options.kernel_user_native_library == NULL
      || options.kernel_user_nosimd_library == NULL
      || options.kernel_library == NULL)
    die("all five backend library options are required");
  if (!options.correctness_only && options.manifest == NULL)
    die("--manifest is required for benchmark mode");
  return options;
}

int
main(int argc, char **argv)
{
  struct options options = parse_options(argc, argv);
  struct backend backends[] = {
    { .name = "user-default", .path = options.default_library,
      .kind = BACKEND_USER },
    { .name = "user-nosimd", .path = options.nosimd_library,
      .kind = BACKEND_USER },
    { .name = "kernel-userspace-native",
      .path = options.kernel_user_native_library,
      .kind = BACKEND_KERNEL },
    { .name = "kernel-userspace-nosimd",
      .path = options.kernel_user_nosimd_library,
      .kind = BACKEND_KERNEL },
    { .name = "kernel-vkso", .path = options.kernel_library,
      .kind = BACKEND_KERNEL },
    { .name = "kernel-userspace-libc", .path = options.kernel_user_libc_library,
      .kind = BACKEND_KERNEL },
  };
  size_t backend_count = ARRAY_SIZE(backends) - (options.kernel_user_libc_library == NULL);

  for (size_t index = 0; index < backend_count; ++index)
    init_backend(&backends[index]);

  if (options.correctness_only) {
    run_correctness(backends, backend_count);
  } else {
    struct corpus corpus = load_corpus(options.manifest);
    int *block_sizes = NULL;
    size_t block_count = parse_block_sizes(options.block_sizes, &block_sizes);
    printf("run,backend,operation,block_size,repeat,input_bytes,"
           "compressed_bytes,elapsed_ns,tsc_ticks,mib_per_second,"
           "ns_per_byte,tsc_per_byte,compression_ratio\n");
    for (size_t block = 0; block < block_count; ++block) {
      for (size_t position = 0; position < backend_count; ++position) {
        size_t backend_index = (position + (size_t)options.order)
                               % backend_count;
        benchmark_backend(&backends[backend_index], &corpus,
                          block_sizes[block], options.warmups,
                          options.repeats, options.run_id);
      }
    }
    fprintf(stderr, "corpus=%zu bytes files=%zu sink=%" PRIu64 "\n",
            corpus.size, corpus.file_count, result_sink);
    free(block_sizes);
    free(corpus.files);
    free(corpus.data);
  }

  for (size_t index = backend_count; index-- > 0;)
    destroy_backend(&backends[index]);
  return EXIT_SUCCESS;
}
