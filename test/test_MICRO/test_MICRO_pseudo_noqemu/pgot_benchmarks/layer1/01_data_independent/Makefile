include ../../common/common.mk

BIN := bench

all: $(BIN)

$(BIN): bench.c ../../common/bench_common.h ../../common/data_tables.h
	$(CC) $(CFLAGS_COMMON) -o $@ bench.c $(LDFLAGS_COMMON)

run: all
	./$(BIN)

clean:
	rm -f $(BIN) *.csv perf-*.txt

.PHONY: all run clean
