/* Diagnostic-only work accounting; absent from uninstrumented builds. */
#ifndef VKSO_SQ_PROFILE_H
#define VKSO_SQ_PROFILE_H
#ifdef VKSO_SQ_PROFILE
struct sq_work_profile {
    unsigned long long raw_calls, raw_bytes, cache_gets, cache_hits, cache_misses;
    unsigned long long codec_calls, codec_input_bytes, codec_output_bytes, codec_ns;
    unsigned long long scatter_calls, scatter_bytes, scatter_ns;
    unsigned long long list_calls, list_entries, lookup_calls, name_hits, new_inodes;
    unsigned long long read_calls, read_bytes;
};
extern struct sq_work_profile sq_work;
unsigned long long sq_profile_clock(void);
#define SQ_COUNT(field, value) (sq_work.field += (value))
#define SQ_START(name) unsigned long long name = sq_profile_clock()
#define SQ_ELAPSED(field, name) SQ_COUNT(field, sq_profile_clock() - (name))
#else
#define SQ_COUNT(field, value) do { } while (0)
#define SQ_START(name) do { } while (0)
#define SQ_ELAPSED(field, name) do { } while (0)
#endif
#endif
