// SPDX-License-Identifier: GPL-2.0
/* Reuse the real public API loops; leave the original reader binary unchanged. */
#define main original_benchmark_main
#include "../baremetal/vkso_time_bench.c"
#undef main
#include <signal.h>
#include <sys/wait.h>

#define MAX_READERS 64
#define MULTI_WINDOW "direct-user-api-multiprocess-batch-v1"

struct result {
	uint64_t start_ns, end_ns, calls, conditioning, cycles, batches, late_batches;
};
static pid_t children[MAX_READERS];
static unsigned int child_count;
static FILE *active_recorder;

static void cleanup_children(void)
{
	unsigned int i;
	if (active_recorder) {
		fputs("stop\n", active_recorder);
		fclose(active_recorder);
		active_recorder = NULL;
	}
	for (i = 0; i < child_count; ++i)
		if (children[i] > 0)
			kill(children[i], SIGTERM);
	for (i = 0; i < child_count; ++i)
		if (children[i] > 0)
			while (waitpid(children[i], NULL, 0) < 0 && errno == EINTR) {}
}

static void interrupted(int signal_number)
{
	(void)signal_number;
	exit(128 + signal_number);
}

static void transfer(int fd, void *buffer, size_t length, int writing)
{
	size_t offset = 0;
	while (offset < length) {
		ssize_t count = writing ? write(fd, (char *)buffer + offset, length - offset) :
			read(fd, (char *)buffer + offset, length - offset);
		if (count < 0 && errno == EINTR)
			continue;
		if (count <= 0)
			fail_message("reader synchronization pipe failed");
		offset += count;
	}
}

static uint64_t now_ns(void)
{
	struct timespec ts;
	if (raw_syscall2(SYS_clock_gettime, CLOCK_MONOTONIC, (long)&ts))
		fail_message("cannot read monotonic time");
	return timespec_to_ns(&ts);
}

static void wait_until(uint64_t deadline)
{
	struct timespec ts = { .tv_sec = deadline / 1000000000ULL,
		.tv_nsec = deadline % 1000000000ULL };
	int error;
	do {
		error = clock_nanosleep(CLOCK_MONOTONIC, TIMER_ABSTIME, &ts, NULL);
	} while (error == EINTR);
	if (error)
		fail_message("clock_nanosleep failed");
}

static struct result worker(enum backend backend, enum operation op,
		unsigned int cpu, unsigned int iterations, unsigned int warmup,
		unsigned int seconds, unsigned int rate, int ready_fd, int start_fd)
{
	enum path path = backend == BACKEND_RAW ? PATH_RAW_VDSO : PATH_VKSO_WRAPPER;
	struct result r = { 0 };
	uint64_t start, deadline, next, checksum = 0;
	struct timespec before, after;
	char ready = 'R';
	pin_cpu(cpu);
	initialize_backend(backend);
	if (public_clock_gettime(operations[op].clock_id, &before))
		fail_message("initial reader call failed");
	checksum += direct_operation_loop(op, path, warmup);
	transfer(ready_fd, &ready, sizeof(ready), 1);
	transfer(start_fd, &start, sizeof(start), 0);
	close(start_fd);
	deadline = start + (uint64_t)seconds * 1000000000ULL;
	next = start;
	wait_until(start);
	r.start_ns = now_ns();
	while (now_ns() < deadline) {
		unsigned int first_cpu, last_cpu;
		uint64_t first, last;
		if (rate) {
			wait_until(next);
			if (now_ns() >= deadline)
				break;
		}
		/* Control syscalls stay outside the measured/conditioned API body. */
		checksum += direct_operation_loop(op, path, warmup);
		first = tsc_begin(&first_cpu);
		checksum += direct_operation_loop(op, path, iterations);
		last = tsc_end(&last_cpu);
		if (first_cpu != last_cpu)
			fail_message("CPU migrated during multi-reader batch");
		r.cycles += last - first;
		r.calls += iterations;
		r.conditioning += warmup;
		r.batches++;
		if (rate) {
			/* Target counts BOTH conditioning and measured calls; batches are bursts. */
			next = start + (uint64_t)((__uint128_t)(r.calls + r.conditioning) *
						1000000000ULL / rate);
			if (now_ns() > next)
				r.late_batches++;
		}
	}
	r.end_ns = now_ns();
	if (!r.calls)
		fail_message("reader window contained no completed batch");
	if (public_clock_gettime(operations[op].clock_id, &after) || after.tv_sec < before.tv_sec ||
	    (after.tv_sec == before.tv_sec && after.tv_nsec < before.tv_nsec))
		fail_message("reader endpoint check failed");
	sink = checksum;
	return r;
}

int main(int argc, char **argv)
{
	unsigned int cpus[MAX_READERS], count = 0, seconds = 15;
	unsigned int iterations = 500000, warmup = 10000, rate = 0, i;
	enum backend backend = BACKEND_RAW;
	enum operation op = OP_CGT_MONOTONIC;
	int ready_pipe[MAX_READERS][2], start_pipe[MAX_READERS][2], backend_set = 0;
	struct result results[MAX_READERS];
	uint64_t start, writer_start = 0, writer_end = 0;
	const char *control = NULL;
	FILE *recorder = NULL;
	for (i = 1; i < (unsigned int)argc; i += 2) {
		if (i + 1 >= (unsigned int)argc)
			fail_message("arguments require values");
		if (!strcmp(argv[i], "--backend")) {
			if (!strcmp(argv[i + 1], "raw")) backend = BACKEND_RAW;
			else if (!strcmp(argv[i + 1], "vkso")) backend = BACKEND_VKSO;
			else fail_message("backend must be raw or vkso");
			backend_set = 1;
		} else if (!strcmp(argv[i], "--cpus")) {
			char *list = strdup(argv[i + 1]), *token, *saved = NULL;
			if (!list) die("strdup");
			for (token = strtok_r(list, ",", &saved); token;
			     token = strtok_r(NULL, ",", &saved)) {
				unsigned int j, cpu = parse_number(token, "CPU", 1);
				if (count == MAX_READERS || cpu >= CPU_SETSIZE)
					fail_message("invalid CPU list");
				for (j = 0; j < count; ++j)
					if (cpus[j] == cpu) fail_message("duplicate reader CPU");
				cpus[count++] = cpu;
			}
			free(list);
		} else if (!strcmp(argv[i], "--seconds")) seconds = parse_number(argv[i + 1], "seconds", 0);
		else if (!strcmp(argv[i], "--iterations")) iterations = parse_number(argv[i + 1], "iterations", 0);
		else if (!strcmp(argv[i], "--warmup")) warmup = parse_number(argv[i + 1], "warmup", 1);
		else if (!strcmp(argv[i], "--rate")) rate = parse_number(argv[i + 1], "rate", 1);
		else if (!strcmp(argv[i], "--writer-control")) control = argv[i + 1];
		else if (!strcmp(argv[i], "--operation")) {
			if (!strcmp(argv[i + 1], "monotonic")) op = OP_CGT_MONOTONIC;
			else if (!strcmp(argv[i + 1], "monotonic_raw")) op = OP_CGT_MONOTONIC_RAW;
			else if (!strcmp(argv[i + 1], "monotonic_coarse")) op = OP_CGT_MONOTONIC_COARSE;
			else fail_message("unsupported operation");
		} else fail_message("unknown argument");
	}
	if (!count || !backend_set)
		fail_message("required: --backend raw|vkso --cpus N[,N...] [--rate calls/s/reader]");
	if (seconds > 3600 || (uint64_t)iterations + warmup > 100000000ULL)
		fail_message("window/batch exceeds supported measurement range");
	atexit(cleanup_children);
	signal(SIGINT, interrupted);
	signal(SIGTERM, interrupted);
	signal(SIGPIPE, SIG_IGN);
	for (i = 0; i < count; ++i) {
		if (pipe(ready_pipe[i]) || pipe(start_pipe[i])) die("pipe");
		children[i] = fork();
		if (children[i] < 0) die("fork");
		if (!children[i]) {
			struct result r;
			child_count = 0;
			close(ready_pipe[i][0]);
			close(start_pipe[i][1]);
			r = worker(backend, op, cpus[i], iterations, warmup, seconds,
				   rate, ready_pipe[i][1], start_pipe[i][0]);
			transfer(ready_pipe[i][1], &r, sizeof(r), 1);
			_exit(0);
		}
		child_count++;
		close(ready_pipe[i][1]);
		close(start_pipe[i][0]);
	}
	for (i = 0; i < count; ++i) {
		char ready;
		transfer(ready_pipe[i][0], &ready, sizeof(ready), 0);
		if (ready != 'R') fail_message("invalid readiness marker");
	}
	start = now_ns() + 100000000ULL;
	for (i = 0; i < count; ++i) {
		transfer(start_pipe[i][1], &start, sizeof(start), 1);
		close(start_pipe[i][1]);
	}
	/* Observe the interior of the common load window, excluding startup/exit. */
	if (control) {
		uint64_t guard = seconds > 2 ? UINT64_C(1000000000) : UINT64_C(100000000);
		wait_until(start + guard);
		recorder = fopen(control, "w");
		if (!recorder) die("open writer recorder");
		active_recorder = recorder;
		writer_start = now_ns();
		if (fputs("start\n", recorder) < 0 || fflush(recorder)) die("start recorder");
		wait_until(start + (uint64_t)seconds * UINT64_C(1000000000) - guard);
		if (fputs("stop\n", recorder) < 0 || fflush(recorder)) die("stop recorder");
		writer_end = now_ns();
		fclose(recorder);
		active_recorder = NULL;
	}
	for (i = 0; i < count; ++i) {
		int status;
		transfer(ready_pipe[i][0], &results[i], sizeof(results[i]), 0);
		close(ready_pipe[i][0]);
		if (waitpid(children[i], &status, 0) < 0 || !WIFEXITED(status) || WEXITSTATUS(status))
			fail_message("reader process failed");
		children[i] = 0;
	}
	puts("backend,api,reader,cpu,readers,scheduled_start_ns,scheduled_end_ns,start_ns,end_ns,measured_calls,conditioning_calls,measured_batches,tsc_cycles_per_call,target_total_calls_per_second,late_batches,writer_start_ns,writer_end_ns,measurement_window");
	for (i = 0; i < count; ++i) {
		struct result *r = &results[i];
		printf("%s,%s,%u,%u,%u,%" PRIu64 ",%" PRIu64 ",%" PRIu64 ",%" PRIu64
		       ",%" PRIu64 ",%" PRIu64 ",%" PRIu64 ",%.9f,%u,%" PRIu64 ",%" PRIu64 ",%" PRIu64 ",%s\n",
		       backend_name(backend), operations[op].name, i, cpus[i], count,
		       start, start + (uint64_t)seconds * UINT64_C(1000000000), r->start_ns, r->end_ns,
		       r->calls, r->conditioning, r->batches, (double)r->cycles / r->calls,
		       rate, r->late_batches, writer_start, writer_end, MULTI_WINDOW);
	}
	return 0;
}
