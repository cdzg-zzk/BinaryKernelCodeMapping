static __always_inline uint32_t rc_bittree(struct rc_dec *rc,
                                         uint16_t *probs, uint32_t limit)
{
    uint32_t symbol = 1;
    unsigned int bits = limit == 8 ? 3 : limit == 64 ? 6 : limit == 256 ? 8 : 0;
#define TREE_STEP() do { \
    if (rc_bit(rc, &probs[symbol])) \
        symbol = (symbol << 1) + 1; \
    else \
        symbol <<= 1; \
} while (0)
    if (bits) {
        TREE_STEP(); TREE_STEP(); TREE_STEP();
        if (bits >= 6) { TREE_STEP(); TREE_STEP(); TREE_STEP(); }
        if (bits == 8) { TREE_STEP(); TREE_STEP(); }
    } else {
        do { TREE_STEP(); } while (symbol < limit);
    }
#undef TREE_STEP
    return symbol;
}
