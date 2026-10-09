#include <stdint.h>
#include <assert.h>
#include <stdio.h>
typedef uint64_t u64;
#define U64_MAX UINT64_MAX
#define likely(x) (x)
static __always_inline u64
before(u64 cycles, u64 cycle_last, u64 mask)
{
	if (likely(mask == U64_MAX)) {
		if (likely(cycles > cycle_last))
			return cycles - cycle_last;
		return 0;
	}
	return (cycles - cycle_last) & mask;
}

static __always_inline u64
after(u64 cycles, u64 cycle_last)
{
	if (likely(cycles > cycle_last))
		return cycles - cycle_last;
	return 0;
}

int main(void) {
    const u64 edges[] = {0,1,2,UINT32_MAX,UINT32_MAX+1ULL,
        (1ULL<<63)-1,(1ULL<<63),(1ULL<<63)+1,UINT64_MAX-1,UINT64_MAX};
    unsigned long checks = 0;
    for (unsigned i=0;i<10;i++) for (unsigned j=0;j<10;j++) {
        u64 c=edges[i],last=edges[j],want=c>last?c-last:0;
        assert(before(c,last,UINT64_MAX)==want && after(c,last)==want); checks++;
    }
    u64 rng=0x412C10C;
    for (unsigned i=0;i<100000;i++) {
        rng=rng*6364136223846793005ULL+1442695040888963407ULL;u64 c=rng;
        rng=rng*6364136223846793005ULL+1442695040888963407ULL;u64 last=rng;
        u64 want=c>last?c-last:0;
        assert(before(c,last,UINT64_MAX)==want && after(c,last)==want);checks++;
    }
    printf("helper_equivalence=PASS cases=%lu mask=UINT64_MAX\n",checks);
}
