/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef APPLICABILITY_ENGINE_H
#define APPLICABILITY_ENGINE_H
#include "protocol.h"
/* Each driver supplies AR_CALLBACK, ar_allocate/free, and standard memory/text APIs. */
struct ar_text { char *data; size_t length, capacity; int error; };
struct ar_stats {
	unsigned int hash_checks, sort_checks, hash_kats;
	int error, failed_case;
	ar_u64 cmp_calls, swap_calls;
};
struct ar_workspace { unsigned char *raw, *input, *expected; };
static struct {
	unsigned char *base;
	size_t num, width;
	int direction, bad_arguments;
	ar_u64 comparisons, swaps;
} ar_callbacks;

static void ar_append(struct ar_text *text, const char *format, ...)
{
	va_list args;
	int n;
	if (text->error) return;
	va_start(args, format);
	n = vsnprintf(text->data + text->length, text->capacity - text->length, format, args);
	va_end(args);
	if (n < 0 || (size_t)n >= text->capacity - text->length) {
		text->error = -ENOSPC;
		return;
	}
	text->length += n;
}

static void ar_hex(struct ar_text *text, const unsigned char *data, size_t length)
{
	static const char digits[] = "0123456789abcdef";
	size_t i;
	if (text->error) return;
	if (2 * length >= text->capacity - text->length) { text->error = -ENOSPC; return; }
	for (i = 0; i < length; ++i) {
		text->data[text->length++] = digits[data[i] >> 4];
		text->data[text->length++] = digits[data[i] & 15];
	}
	text->data[text->length] = '\0';
}

static int ar_valid_element(const void *pointer)
{
	unsigned long p = (unsigned long)pointer, base = (unsigned long)ar_callbacks.base;
	return p >= base && p < base + ar_callbacks.num * ar_callbacks.width &&
		(p - base) % ar_callbacks.width == 0;
}

static AR_CALLBACK int ar_comparator(const void *a, const void *b)
{
	ar_callbacks.comparisons++;
	if (!ar_valid_element(a) || !ar_valid_element(b)) {
		ar_callbacks.bad_arguments = 1;
		return 0;
	}
	return ar_compare_bytes(a, b, ar_callbacks.width, ar_callbacks.direction);
}

static AR_CALLBACK void ar_swapper(void *a, void *b, int size)
{
	unsigned char *x = a, *y = b;
	int i;
	ar_callbacks.swaps++;
	if (size != (int)ar_callbacks.width || !ar_valid_element(a) || !ar_valid_element(b)) {
		ar_callbacks.bad_arguments = 1;
		return;
	}
	for (i = 0; i < size; ++i) { unsigned char saved = x[i]; x[i] = y[i]; y[i] = saved; }
}

static int ar_guards(const unsigned char *raw, size_t start, size_t length)
{
	size_t i;
	for (i = 0; i < AR_RAW_SIZE; ++i)
		if ((i < start || i >= start + length) && raw[i] != 0xa5) return 0;
	return 1;
}

static int ar_hash_case(ar_hash_fn function, struct ar_workspace *w, struct ar_text *text,
			struct ar_stats *stats, unsigned int id, int kat, size_t length,
			unsigned int alignment, ar_u32 seed)
{
	unsigned char *data = w->raw + AR_GUARD + alignment;
	ar_u32 expected, actual;
	int intact, guards, passed;
	memset(w->raw, 0xa5, AR_RAW_SIZE);
	if (kat >= 0) memcpy(data, ar_kats[kat].input, length);
	else ar_hash_input(data, length, seed);
	memcpy(w->input, data, length);
	expected = ar_reference_hash(data, length, seed);
	if (kat >= 0 && expected != ar_kats[kat].expected) return -EPROTO;
	actual = function(data, length, seed);
	intact = memcmp(data, w->input, length) == 0;
	guards = ar_guards(w->raw, AR_GUARD + alignment, length);
	passed = intact && guards && actual == expected;
	ar_append(text, "%u,%s,%zu,%u,%u,", id, kat >= 0 ? "known-answer" : "boundary", length, alignment, seed);
	ar_hex(text, w->input, length);
	ar_append(text, ",%u,%u,%d,%d,%d\n", expected, actual, intact, guards, passed);
	if (!passed || text->error) return text->error ? text->error : -EBADMSG;
	stats->hash_checks++;
	if (kat >= 0) stats->hash_kats++;
	return 0;
}

static int ar_run_hash(ar_hash_fn function, struct ar_workspace *w, struct ar_text *text, struct ar_stats *stats)
{
	unsigned int i, a, s, id = 0;
	int result;
	for (i = 0; i < AR_COUNT(ar_kats); ++i, ++id) {
		result = ar_hash_case(function, w, text, stats, id, i, strlen(ar_kats[i].input), 0, 0);
		if (result) goto fail;
	}
	for (i = 0; i < AR_COUNT(ar_lengths); ++i)
		for (a = 0; a < AR_COUNT(ar_hash_alignments); ++a)
			for (s = 0; s < AR_COUNT(ar_seeds); ++s, ++id) {
				result = ar_hash_case(function, w, text, stats, id, -1, ar_lengths[i], ar_hash_alignments[a], ar_seeds[s]);
				if (result) goto fail;
			}
	return stats->hash_checks == AR_HASH_CHECKS ? 0 : -EPROTO;
fail:
	stats->failed_case = id;
	return result;
}

static int ar_multiset(const unsigned char *before, const unsigned char *after, size_t num, size_t width)
{
	size_t i, j;
	for (i = 0; i < num; ++i) {
		unsigned int a = 0, b = 0;
		for (j = 0; j < num; ++j) {
			a += memcmp(before + i * width, before + j * width, width) == 0;
			b += memcmp(before + i * width, after + j * width, width) == 0;
		}
		if (a != b) return 0;
	}
	return 1;
}

static int ar_sort_case(ar_sort_fn function, struct ar_workspace *w, struct ar_text *text,
			struct ar_stats *stats, unsigned int id, size_t num, size_t width,
			unsigned int alignment, unsigned int pattern, int direction, int custom)
{
	unsigned char *data = w->raw + AR_GUARD + alignment;
	size_t length = num * width, i;
	int guards, sorted = 1, permutation, exact, passed;
	memset(w->raw, 0xa5, AR_RAW_SIZE);
	ar_sort_input(data, num, width, pattern);
	memcpy(w->input, data, length);
	memcpy(w->expected, data, length);
	ar_reference_sort(w->expected, num, width, direction);
	memset(&ar_callbacks, 0, sizeof(ar_callbacks));
	ar_callbacks.base = data; ar_callbacks.num = num; ar_callbacks.width = width; ar_callbacks.direction = direction;
	function(data, num, width, ar_comparator, custom ? ar_swapper : NULL);
	guards = ar_guards(w->raw, AR_GUARD + alignment, length);
	for (i = 1; i < num; ++i)
		if (ar_compare_bytes(data + (i - 1) * width, data + i * width, width, direction) > 0) sorted = 0;
	permutation = ar_multiset(w->input, data, num, width);
	exact = memcmp(data, w->expected, length) == 0;
	passed = guards && sorted && permutation && exact && !ar_callbacks.bad_arguments &&
		(num >= 2 || (!ar_callbacks.comparisons && !ar_callbacks.swaps));
	ar_append(text, "%u,%zu,%zu,%u,%s,%d,%s,", id, num, width, alignment, ar_patterns[pattern], direction, custom ? "custom" : "default");
	ar_hex(text, w->input, length); ar_append(text, ",");
	ar_hex(text, w->expected, length); ar_append(text, ","); ar_hex(text, data, length);
	ar_append(text, ",%llu,%llu,%lu,%lu,%d,%d,%d,%d,%d,%d\n",
		(unsigned long long)ar_callbacks.comparisons, (unsigned long long)ar_callbacks.swaps,
		(unsigned long)ar_comparator, custom ? (unsigned long)ar_swapper : 0,
		guards, sorted, permutation, exact, !ar_callbacks.bad_arguments, passed);
	if (!passed || text->error) { stats->failed_case = id; return text->error ? text->error : -EBADMSG; }
	stats->sort_checks++;
	stats->cmp_calls += ar_callbacks.comparisons; stats->swap_calls += ar_callbacks.swaps;
	return 0;
}

static int ar_run_sort(ar_sort_fn function, struct ar_workspace *w, struct ar_text *text, struct ar_stats *stats)
{
	unsigned int n, width, alignment, pattern, direction, custom, id = 0;
	int result;
	for (n = 0; n < AR_COUNT(ar_counts); ++n)
	for (width = 0; width < AR_COUNT(ar_widths); ++width)
	for (alignment = 0; alignment < 2; ++alignment)
	for (pattern = 0; pattern < 4; ++pattern)
	for (direction = 0; direction < 2; ++direction)
	for (custom = 0; custom < 2; ++custom, ++id) {
		result = ar_sort_case(function, w, text, stats, id, ar_counts[n], ar_widths[width],
			alignment, pattern, direction ? -1 : 1, custom);
		if (result) return result;
	}
	return stats->sort_checks == AR_SORT_CHECKS ? 0 : -EPROTO;
}

static void ar_headers(struct ar_text *hash, struct ar_text *sort)
{
	ar_append(hash, "case_id,vector_kind,length,alignment,seed,input_hex,expected,actual,input_unchanged,guards_ok,pass\n");
	ar_append(sort, "case_id,num,width,alignment,pattern,direction,swap_mode,input_hex,expected_hex,actual_hex,cmp_calls,swap_calls,cmp_address,swap_address,guards_ok,sorted_ok,permutation_ok,exact_match,callback_arguments_ok,pass\n");
}

static int ar_execute(unsigned int roots, ar_hash_fn hash, ar_sort_fn sort,
		      struct ar_text *hash_text, struct ar_text *sort_text, struct ar_stats *stats)
{
	struct ar_workspace w = {0};
	int result = 0;
	stats->failed_case = -1;
	w.raw = ar_allocate(AR_RAW_SIZE);
	w.input = ar_allocate(AR_MAX_HASH);
	w.expected = ar_allocate(AR_MAX_HASH);
	if (!w.raw || !w.input || !w.expected) { result = -ENOMEM; goto done; }
	if (roots & 1) { result = ar_run_hash(hash, &w, hash_text, stats); if (result) goto done; }
	if (roots & 2) result = ar_run_sort(sort, &w, sort_text, stats);
done:
	ar_release(w.raw); ar_release(w.input); ar_release(w.expected);
	memset(&ar_callbacks, 0, sizeof(ar_callbacks));
	stats->error = result;
	return result;
}
#endif
