/* SPDX-License-Identifier: GPL-2.0-only */
/* Observation driver: the BCH algorithm and original workload helpers stay unchanged. */
#define _GNU_SOURCE
#include <elf.h>
#include <link.h>
#include <malloc.h>
#include <stdarg.h>
#include <stddef.h>
#include <limits.h>

#define main bch_original_main
#include "../test_BCH/src/bch_bench.c"
#undef main
#include "../test_BCH/userspace/kernel_compat.h"
#include "../test_BCH/vendor/linux-5.15/include/linux/bch.h"

/* Exact private layouts from adapted/bch.c:123-136, for allocation sizes only. */
struct gf_poly {
	unsigned int deg;
	unsigned int c[];
};
struct gf_poly_deg1 {
	struct gf_poly poly;
	unsigned int c[2];
};

#ifndef PROBE_BENCH_SHA256
#define PROBE_BENCH_SHA256 "unrecorded"
#endif
#ifndef PROBE_ADAPTED_SHA256
#define PROBE_ADAPTED_SHA256 "unrecorded"
#endif
#ifndef PROBE_HEADER_SHA256
#define PROBE_HEADER_SHA256 "unrecorded"
#endif
#ifndef PROBE_SHIM_SHA256
#define PROBE_SHIM_SHA256 "unrecorded"
#endif

_Static_assert(sizeof(void *) == 8 && sizeof(unsigned int) == 4,
	       "This observer targets the existing x86-64 Linux 5.15 BCH build");
_Static_assert(sizeof(struct gf_poly) == 4 && sizeof(struct gf_poly_deg1) == 12,
	       "Unexpected polynomial allocation layout");
_Static_assert(offsetof(struct bch_public, ecc_bytes) ==
	       offsetof(struct bch_control, ecc_bytes), "BCH public prefix mismatch");

static struct backend observed_backend;
static struct bench_case observed_cases[CASE_COUNT] = {
	{.m = 13, .t = 4, .len = 512}, {.m = 13, .t = 8, .len = 512},
};
static struct op_context active_context;
static unsigned int active_vector[MAX_T];
static uint64_t active_seed;
static char observed_path[PATH_MAX];
static char report_buffer[32768];
static const char *stage = "unloaded";
static int active_case = -1;
static int last_errno;
static bool initialized;
static bool allocator_verified;
static unsigned int verification_checks[CASE_COUNT];
static unsigned int geometry_checks;
static void *libc_handle;
static void *allocator_addresses[4];
static void *allocator_import_addresses[3];
static void *shim_import_addresses[3];
static void *carrier_helper_addresses[2];
static uintptr_t carrier_slot_addresses[2];
static size_t report_used;
static bool report_overflow;
static size_t live_allocation_count;
static size_t live_requested_bytes;
static size_t live_usable_bytes;

static int probe_error(int number)
{
	last_errno = number;
	return -number;
}

static void append(const char *format, ...)
{
	int size;
	va_list args;

	if (report_overflow)
		return;
	va_start(args, format);
	size = vsnprintf(report_buffer + report_used,
			 sizeof(report_buffer) - report_used, format, args);
	va_end(args);
	if (size < 0 || (size_t)size >= sizeof(report_buffer) - report_used) {
		report_overflow = true;
		return;
	}
	report_used += (size_t)size;
}

static void append_string(const char *string)
{
	const unsigned char *p = (const unsigned char *)string;
	append("\"");
	for (; *p; ++p) {
		if (*p == '\\' || *p == '"')
			append("\\%c", *p);
		else if (*p < 32 || *p >= 127)
			append("\\u%04x", *p);
		else
			append("%c", *p);
	}
	append("\"");
}

/* Read only the already loaded DSO's public ELF dynamic relocations. This is
 * needed because a dlsym result alone does not prove the imported slot binding.
 * link_map.l_addr is the ELF load bias, including for the sparse carrier whose
 * first PT_LOAD virtual address is nonzero. No kernel address lookup is used. */
static int check_allocator_relocations(struct link_map *map, Elf64_Rela *rela,
				       size_t bytes, Elf64_Sym *symbols,
				       const char *strings, bool carrier,
				       unsigned int *seen, void **import_targets)
{
	const char *native_names[] = {"malloc", "calloc", "free"};
	const char *carrier_names[] = {"__kmalloc", "kfree"};
	size_t i;

	if (bytes % sizeof(*rela) || bytes > 1024 * 1024)
		return probe_error(EPROTO);
	for (i = 0; i < bytes / sizeof(*rela); ++i) {
		unsigned int type = ELF64_R_TYPE(rela[i].r_info);
		const char *name = strings + symbols[ELF64_R_SYM(rela[i].r_info)].st_name;
		unsigned int index;
		if (type != R_X86_64_64 && type != R_X86_64_JUMP_SLOT &&
		    type != R_X86_64_GLOB_DAT)
			continue;
		for (index = 0; index < (carrier ? 2U : 3U); ++index) {
			uintptr_t slot;
			void *target, *expected;
			if (strcmp(name, carrier ? carrier_names[index] : native_names[index]))
				continue;
			if (rela[i].r_addend)
				return probe_error(EPROTO);
			slot = (uintptr_t)map->l_addr + rela[i].r_offset;
			memcpy(&target, (void *)slot, sizeof(target));
			expected = carrier ? carrier_helper_addresses[index] :
				allocator_addresses[index];
			if (target != expected)
				return probe_error(EPROTO);
			if (carrier)
				carrier_slot_addresses[index] = slot;
			else
				import_targets[index] = target;
			*seen |= 1U << index;
		}
	}
	return 0;
}

static int verify_dynamic_imports(void *handle, bool carrier,
				 unsigned int required, void **import_targets)
{
	struct link_map *map = NULL;
	Elf64_Dyn *entry;
	Elf64_Sym *symbols = NULL;
	Elf64_Rela *rela = NULL, *plt = NULL;
	const char *strings = NULL;
	size_t rela_bytes = 0, plt_bytes = 0;
	unsigned int i, seen = 0;
	long plt_kind = DT_RELA;

	if (dlinfo(handle, RTLD_DI_LINKMAP, &map) || !map)
		return probe_error(ELIBBAD);
	for (entry = map->l_ld, i = 0; i < 4096 && entry->d_tag != DT_NULL;
	     ++entry, ++i) {
		switch (entry->d_tag) {
		case DT_SYMTAB: symbols = (void *)entry->d_un.d_ptr; break;
		case DT_STRTAB: strings = (void *)entry->d_un.d_ptr; break;
		case DT_RELA: rela = (void *)entry->d_un.d_ptr; break;
		case DT_RELASZ: rela_bytes = entry->d_un.d_val; break;
		case DT_JMPREL: plt = (void *)entry->d_un.d_ptr; break;
		case DT_PLTRELSZ: plt_bytes = entry->d_un.d_val; break;
		case DT_PLTREL: plt_kind = entry->d_un.d_val; break;
		}
	}
	if (i == 4096 || !symbols || !strings || (rela_bytes && !rela) ||
	    (plt_bytes && (!plt || plt_kind != DT_RELA)))
		return probe_error(ELIBBAD);
	if (check_allocator_relocations(map, rela, rela_bytes, symbols, strings,
					carrier, &seen, import_targets) ||
	    check_allocator_relocations(map, plt, plt_bytes, symbols, strings,
					carrier, &seen, import_targets))
		return -last_errno;
	if ((seen & required) != required)
		return probe_error(EPROTO);
	return 0;
}

static int verify_allocator(bool carrier)
{
	const char *names[] = {"malloc", "calloc", "free", "malloc_usable_size"};
	unsigned int i;
	libc_handle = dlopen("libc.so.6", RTLD_NOW | RTLD_LOCAL);
	if (!libc_handle)
		return probe_error(ELIBACC);
	for (i = 0; i < 4; ++i) {
		allocator_addresses[i] = dlvsym(libc_handle, names[i], "GLIBC_2.2.5");
		if (!allocator_addresses[i] ||
		    dlsym(RTLD_DEFAULT, names[i]) != allocator_addresses[i] ||
		    dlsym(observed_backend.handle, names[i]) != allocator_addresses[i])
			return probe_error(EPROTO);
	}
	if (carrier) {
		const char *helper_names[] = {"__kmalloc", "kfree"};
		for (i = 0; i < 2; ++i) {
			Dl_info info;
			const char *base;
			void *shim_handle;
			int result;
			carrier_helper_addresses[i] = dlsym(observed_backend.handle,
							 helper_names[i]);
			if (!carrier_helper_addresses[i] ||
			    !dladdr(carrier_helper_addresses[i], &info))
				return probe_error(EPROTO);
			base = strrchr(info.dli_fname, '/');
			base = base ? base + 1 : info.dli_fname;
			if (strcmp(base, "libshim.so"))
				return probe_error(EPROTO);
			/* Inspect the helper's actual DSO, not an independently loaded shim. */
			shim_handle = dlopen(info.dli_fname, RTLD_NOW | RTLD_NOLOAD);
			if (!shim_handle)
				return probe_error(ELIBBAD);
			result = verify_dynamic_imports(shim_handle, false, 5U,
						shim_import_addresses);
			dlclose(shim_handle);
			if (result)
				return result;
		}
	}
	if (verify_dynamic_imports(observed_backend.handle, carrier,
				   carrier ? 3U : 7U, allocator_import_addresses))
		return -last_errno;
	allocator_verified = true;
	return 0;
}

int probe_load(const char *path, int carrier)
{
	if (!path || !*path || strlen(path) >= sizeof(observed_path) ||
	    (carrier != 0 && carrier != 1))
		return probe_error(EINVAL);
	if (observed_backend.handle)
		return probe_error(EALREADY);
	strcpy(observed_path, path);
	observed_backend.name = carrier ? "kernel-vkso" : "kernel-native";
	observed_backend.path = observed_path;
	/* Original symbol selection, dlopen flags and hard failure behavior. */
	load_backend(&observed_backend);
	stage = "loaded";
	if (verify_allocator(carrier)) {
		stage = "allocator-rejected";
		return -last_errno;
	}
	last_errno = 0;
	return 0;
}

int probe_initialize(void)
{
	int c, i;
	if (!allocator_verified)
		return probe_error(EPERM);
	if (initialized)
		return probe_error(EALREADY);
	stage = "initializing";
	/* Set this before allocation so probe_release also handles partial setup. */
	initialized = true;
	for (c = 0; c < CASE_COUNT; ++c) {
		struct bench_case *test = &observed_cases[c];
		struct bch_control *control;
		uint64_t seed = UINT64_C(0xb4c00000) + (uint64_t)c;
		control = new_control(&observed_backend, test->m, test->t);
		test->controls[0] = control;
		if (control->m != 13 || control->n != 8191 ||
		    control->t != (unsigned int)test->t || control->swap_bits ||
		    control->ecc_bits != (unsigned int)(test->m * test->t) ||
		    control->ecc_bytes != (unsigned int)((test->m * test->t + 7) / 8))
			return probe_error(EPROTO);
		geometry_checks++;
		test->ecc_bits = control->ecc_bits;
		test->ecc_bytes = control->ecc_bytes;
		test->codeword = xcalloc((size_t)test->len + test->ecc_bytes, 1);
		/* Same seeded codeword construction as original initialize_cases;
		 * only one observed backend is instantiated in this loader process. */
		for (i = 0; i < test->len; ++i)
			test->codeword[i] = (uint8_t)prng_next(&seed);
		observed_backend.encode(control, test->codeword, test->len,
					test->codeword + test->len);
	}
	stage = "initialized";
	last_errno = 0;
	return 0;
}

int probe_activate(int case_index)
{
	struct bench_case *test;
	if (!initialized || geometry_checks < 2 || case_index < 0 ||
	    case_index >= CASE_COUNT)
		return probe_error(EINVAL);
	if (active_case != -1)
		return probe_error(EBUSY);
	test = &observed_cases[case_index];
	active_context = (struct op_context){
		.backend = &observed_backend, .control = test->controls[0],
		.test = test, .mode = MODE_DECODE_FULL, .errors = test->t,
	};
	active_case = case_index;
	/* Original correctness workload, trial 0, errors=t. */
	active_seed = UINT64_C(0x63c5a17e9b) ^ ((uint64_t)case_index << 48) ^
		(uint64_t)test->t;
	generate_error_vector(active_vector, test->t,
		8U * (unsigned int)test->len + test->ecc_bits, active_seed);
	stage = "activating";
	prepare_decode_context(&active_context, active_vector);
	verify_decode(&active_context, active_vector);
	verification_checks[case_index]++;
	stage = "active";
	last_errno = 0;
	return 0;
}

int probe_deactivate(void)
{
	if (active_case == -1)
		return probe_error(EINVAL);
	free_decode_context(&active_context);
	memset(&active_context, 0, sizeof(active_context));
	active_case = -1;
	stage = "deactivated";
	last_errno = 0;
	return 0;
}

int probe_release(void)
{
	int c;
	if (!observed_backend.handle)
		return probe_error(EINVAL);
	if (active_case != -1)
		probe_deactivate();
	for (c = 0; c < CASE_COUNT; ++c) {
		struct bench_case *test = &observed_cases[c];
		free(test->codeword);
		test->codeword = NULL;
		if (test->controls[0])
			observed_backend.free_control(test->controls[0]);
		test->controls[0] = NULL;
	}
	initialized = false;
	stage = "released";
	last_errno = 0;
	/* Both the backend and libc handles stay loaded for the released snapshot. */
	return 0;
}

static void append_allocation(int c, const char *category, const char *name,
			      void *address, size_t requested)
{
	size_t usable;
	if (!address || !allocator_verified) {
		last_errno = EPROTO;
		return;
	}
	usable = malloc_usable_size(address);
	if (usable < requested)
		last_errno = EPROTO;
	append("%s{\"case_index\":%d,\"t\":%d,\"category\":\"%s\","
	       "\"name\":\"%s\",\"address\":%" PRIuPTR ","
	       "\"requested_bytes\":%zu,\"usable_bytes\":%zu}",
	       live_allocation_count ? "," : "", c, observed_cases[c].t,
	       category, name, (uintptr_t)address, requested, usable);
	live_allocation_count++;
	live_requested_bytes += requested;
	live_usable_bytes += usable;
}

static void append_control_allocations(int c)
{
	struct bch_control *bch = observed_cases[c].controls[0];
	static const char *poly_names[] = {"poly_2t[0]", "poly_2t[1]",
		"poly_2t[2]", "poly_2t[3]"};
	size_t words;
	int i;
	if (!bch)
		return;
	words = (bch->m * bch->t + 31) / 32;
#define ALLOCATION(name, bytes) \
	append_allocation(c, "control", #name, bch->name, (bytes))
	append_allocation(c, "control", "bch_control", bch, sizeof(*bch));
	ALLOCATION(a_pow_tab, (1 + bch->n) * sizeof(*bch->a_pow_tab));
	ALLOCATION(a_log_tab, (1 + bch->n) * sizeof(*bch->a_log_tab));
	ALLOCATION(mod8_tab, words * 1024 * sizeof(*bch->mod8_tab));
	ALLOCATION(ecc_buf, words * sizeof(*bch->ecc_buf));
	ALLOCATION(ecc_buf2, words * sizeof(*bch->ecc_buf2));
	ALLOCATION(xi_tab, bch->m * sizeof(*bch->xi_tab));
	ALLOCATION(syn, 2 * bch->t * sizeof(*bch->syn));
	ALLOCATION(cache, 2 * bch->t * sizeof(*bch->cache));
	ALLOCATION(elp, (bch->t + 1) * sizeof(struct gf_poly_deg1));
#undef ALLOCATION
	for (i = 0; i < 4; ++i)
		append_allocation(c, "control", poly_names[i], bch->poly_2t[i],
			sizeof(struct gf_poly) + (2 * bch->t + 1) * sizeof(unsigned int));
}

const char *probe_report(void)
{
	int c, i;
	bool report_failed;
	report_used = 0;
	report_overflow = false;
	live_allocation_count = live_requested_bytes = live_usable_bytes = 0;
	append("{\"schema_version\":1,\"stage\":\"%s\",\"backend\":\"%s\","
	       "\"active_case\":%d,\"allocator_verified\":%s,\"dso_path\":",
	       stage, observed_backend.name ? observed_backend.name : "none",
	       active_case, allocator_verified ? "true" : "false");
	append_string(observed_path);
	append(",\"api_symbols\":{\"init\":\"%sbch_init\",\"free\":\"%sbch_free\","
	       "\"encode\":\"%sbch_encode\",\"decode\":\"%sbch_decode\"}",
	       carrier_helper_addresses[0] ? "vkso_" : "",
	       carrier_helper_addresses[0] ? "vkso_" : "",
	       carrier_helper_addresses[0] ? "vkso_" : "",
	       carrier_helper_addresses[0] ? "vkso_" : "");
	append(",\"api_addresses\":{\"init\":%" PRIuPTR ",\"free\":%" PRIuPTR
	       ",\"encode\":%" PRIuPTR ",\"decode\":%" PRIuPTR "},",
	       (uintptr_t)observed_backend.init4, (uintptr_t)observed_backend.free_control,
	       (uintptr_t)observed_backend.encode, (uintptr_t)observed_backend.decode);
	append("\"allocator\":{\"malloc\":%" PRIuPTR ",\"calloc\":%" PRIuPTR
	       ",\"free\":%" PRIuPTR ",\"malloc_usable_size\":%" PRIuPTR
	       ",\"native_import_targets\":[%" PRIuPTR ",%" PRIuPTR ",%" PRIuPTR
	       "],\"shim_import_targets\":[%" PRIuPTR ",%" PRIuPTR ",%" PRIuPTR
	       "],\"carrier_helper_targets\":[%" PRIuPTR ",%" PRIuPTR
	       "],\"carrier_slot_addresses\":[%" PRIuPTR ",%" PRIuPTR "]},",
	       (uintptr_t)allocator_addresses[0], (uintptr_t)allocator_addresses[1],
	       (uintptr_t)allocator_addresses[2], (uintptr_t)allocator_addresses[3],
	       (uintptr_t)allocator_import_addresses[0], (uintptr_t)allocator_import_addresses[1],
	       (uintptr_t)allocator_import_addresses[2], (uintptr_t)shim_import_addresses[0],
	       (uintptr_t)shim_import_addresses[1], (uintptr_t)shim_import_addresses[2],
	       (uintptr_t)carrier_helper_addresses[0],
	       (uintptr_t)carrier_helper_addresses[1], carrier_slot_addresses[0], carrier_slot_addresses[1]);
	append("\"source_identity\":{\"bench_sha256\":\"%s\",\"adapted_sha256\":\"%s\","
	       "\"header_sha256\":\"%s\",\"shim_sha256\":\"%s\"},",
	       PROBE_BENCH_SHA256, PROBE_ADAPTED_SHA256, PROBE_HEADER_SHA256, PROBE_SHIM_SHA256);
	append("\"abi\":{\"pointer_bytes\":%zu,\"unsigned_int_bytes\":%zu,"
	       "\"bch_control_bytes\":%zu,\"gf_poly_bytes\":%zu,\"gf_poly_deg1_bytes\":%zu,"
	       "\"offsets\":{", sizeof(void *), sizeof(unsigned int),
	       sizeof(struct bch_control), sizeof(struct gf_poly), sizeof(struct gf_poly_deg1));
#define OFFSET(field) append("\"" #field "\":%zu,", offsetof(struct bch_control, field))
	OFFSET(m); OFFSET(n); OFFSET(t); OFFSET(ecc_bits); OFFSET(ecc_bytes);
	OFFSET(a_pow_tab); OFFSET(a_log_tab); OFFSET(mod8_tab); OFFSET(ecc_buf);
	OFFSET(ecc_buf2); OFFSET(xi_tab); OFFSET(syn); OFFSET(cache); OFFSET(elp);
	OFFSET(poly_2t);
#undef OFFSET
	append("\"swap_bits\":%zu}},\"geometry_checks\":%u,\"verification_checks\":%u,\"cases\":[",
	       offsetof(struct bch_control, swap_bits), geometry_checks,
	       verification_checks[0] + verification_checks[1]);
	for (c = 0; c < CASE_COUNT; ++c) {
		struct bench_case *test = &observed_cases[c];
		append("%s{\"case_index\":%d,\"m\":%d,\"t\":%d,\"len\":%d,\"ecc_bits\":%u,"
		       "\"ecc_bytes\":%u,\"codeword_seed\":%" PRIu64 ",\"verification_checks\":%u}",
		       c ? "," : "", c, test->m, test->t, test->len, test->ecc_bits,
		       test->ecc_bytes, UINT64_C(0xb4c00000) + (uint64_t)c, verification_checks[c]);
	}
	append("],\"active_vector\":");
	if (active_case == -1)
		append("null");
	else {
		append("{\"mode\":\"decode-full\",\"trial\":0,\"errors\":%d,\"seed\":%" PRIu64
		       ",\"positions\":[", active_context.errors, active_seed);
		for (i = 0; i < active_context.errors; ++i)
			append("%s%u", i ? "," : "", active_vector[i]);
		append("],\"verified_returned_positions\":[");
		for (i = 0; i < active_context.errors; ++i)
			append("%s%u", i ? "," : "", active_context.errloc[i]);
		append("]}");
	}
	append(",\"allocations\":[");
	for (c = 0; c < CASE_COUNT; ++c) {
		struct bench_case *test = &observed_cases[c];
		append_control_allocations(c);
		if (test->codeword)
			append_allocation(c, "workload", "codeword", test->codeword,
				(size_t)test->len + test->ecc_bytes);
	}
	if (active_case != -1) {
		struct bench_case *test = &observed_cases[active_case];
		append_allocation(active_case, "workload", "work", active_context.work,
			(size_t)test->len + test->ecc_bytes);
		append_allocation(active_case, "workload", "difference", active_context.difference,
			test->ecc_bytes);
		append_allocation(active_case, "workload", "errloc", active_context.errloc,
			(size_t)test->t * sizeof(*active_context.errloc));
	}
	report_failed = last_errno != 0;
	append("],\"live_allocation_count\":%zu,\"live_requested_bytes\":%zu,"
	       "\"live_usable_bytes\":%zu,\"last_errno\":%d,\"report_ok\":%s}",
	       live_allocation_count, live_requested_bytes, live_usable_bytes,
	       last_errno, report_failed ? "false" : "true");
	if (report_overflow) {
		last_errno = EOVERFLOW;
		strcpy(report_buffer, "{\"schema_version\":1,\"report_ok\":false,\"last_errno\":75,"
			"\"error\":\"static report buffer overflow\"}");
	}
	return report_buffer;
}
