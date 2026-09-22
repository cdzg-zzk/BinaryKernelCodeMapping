#include "official_backend_adapter.h"

#include <errno.h>
#include <limits.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "bench.h"

static void
usage(const char *program)
{
	fprintf(stderr,
		"usage: %s --library PATH --api user|kernel --block-size BYTES "
		"--seconds N -- FILE...\n",
		program);
}

static unsigned long
parse_unsigned(const char *text, const char *option)
{
	char *end = NULL;
	unsigned long value;

	errno = 0;
	value = strtoul(text, &end, 10);
	if (errno != 0 || text[0] == '\0' || *end != '\0' || value == 0) {
		fprintf(stderr, "invalid %s value: %s\n", option, text);
		exit(EXIT_FAILURE);
	}
	return value;
}

int
main(int argc, char **argv)
{
	const char *library = NULL;
	const char *api = NULL;
	unsigned long block_size = 0;
	unsigned long seconds = 0;
	int file_index = 0;

	for (int index = 1; index < argc; ++index) {
		if (strcmp(argv[index], "--") == 0) {
			file_index = index + 1;
			break;
		}
		if (index + 1 >= argc) {
			usage(argv[0]);
			return EXIT_FAILURE;
		}
		if (strcmp(argv[index], "--library") == 0)
			library = argv[++index];
		else if (strcmp(argv[index], "--api") == 0)
			api = argv[++index];
		else if (strcmp(argv[index], "--block-size") == 0)
			block_size = parse_unsigned(argv[++index], "--block-size");
		else if (strcmp(argv[index], "--seconds") == 0)
			seconds = parse_unsigned(argv[++index], "--seconds");
		else {
			usage(argv[0]);
			return EXIT_FAILURE;
		}
	}

	if (library == NULL || api == NULL || block_size == 0 || seconds == 0
		|| file_index == 0 || file_index >= argc
		|| block_size > SIZE_MAX || seconds > UINT_MAX
		|| (strcmp(api, "user") != 0 && strcmp(api, "kernel") != 0)) {
		usage(argv[0]);
		return EXIT_FAILURE;
	}

	if (official_backend_open(library, strcmp(api, "kernel") == 0) != 0)
		return EXIT_FAILURE;
	BMK_setNotificationLevel(1);
	BMK_setBenchSeparately(0);
	BMK_setBlockSize((size_t)block_size);
	BMK_setNbSeconds((unsigned)seconds);
	fprintf(stderr, "official_harness=lz4-1.9.3/programs/bench.c\n");
	int result = BMK_benchFiles(
		(const char **)&argv[file_index], (unsigned)(argc - file_index),
		1, 1, NULL);
	official_backend_close();
	return result == 0 ? EXIT_SUCCESS : EXIT_FAILURE;
}
