include ../../common/common.mk

BIN_NORET := bench_noret
BIN_RET := bench_retpoline

all: $(BIN_NORET) $(BIN_RET)

$(BIN_NORET): bench.c ../../common/bench_common.h ../../common/targets.h
	$(CC) $(CFLAGS_COMMON) -o $@ bench.c $(LDFLAGS_COMMON)

$(BIN_RET): bench.c ../../common/bench_common.h ../../common/targets.h
	$(CC) $(CFLAGS_COMMON) $(RETPOLINE_CFLAGS) -o $@ bench.c $(LDFLAGS_COMMON)

run: all
	./$(BIN_NORET)
	./$(BIN_RET)

clean:
	rm -f $(BIN_NORET) $(BIN_RET) *.csv perf-*.txt

.PHONY: all run clean
