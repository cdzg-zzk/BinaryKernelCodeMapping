CC ?= gcc
CFLAGS ?= -O3 -Wall -Wextra -std=c11
LDLIBS ?= -ldl -lm

.PHONY: all clean

all: benchmark_first_touch benchmark_pmc benchmark_ftrace

benchmark_first_touch: benchmark_first_touch.c
	$(CC) $(CFLAGS) $< -o $@ $(LDLIBS)

benchmark_pmc: benchmark_pmc.c
	$(CC) $(CFLAGS) $< -o $@ $(LDLIBS)

benchmark_ftrace: benchmark_ftrace.c
	$(CC) $(CFLAGS) $< -o $@ $(LDLIBS)

clean:
	rm -f benchmark_first_touch benchmark_pmc benchmark_ftrace
