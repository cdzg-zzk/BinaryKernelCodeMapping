/* Diagnostic hypothesis: select both probability/range outcomes using scalar
 * masks. No result is assumed: extra arithmetic/register pressure may lose to
 * predicted branches. Integer rounding exactly matches each original arm. */
static __always_inline int rc_bit(struct rc_dec *rc, uint16_t *prob)
{
	uint32_t bound, mask, value, up, down;
	int bit;

	rc_normalize(rc);
	value = *prob;
	bound = (rc->range >> RC_BIT_MODEL_TOTAL_BITS) * value;
	bit = rc->code >= bound;
	mask = (uint32_t)0 - (uint32_t)bit;
	rc->range = (bound & ~mask) | ((rc->range - bound) & mask);
	rc->code -= bound & mask;
	up = (RC_BIT_MODEL_TOTAL - value) >> RC_MOVE_BITS;
	down = value >> RC_MOVE_BITS;
	*prob = value + (up & ~mask) - (down & mask);
	return bit;
}
