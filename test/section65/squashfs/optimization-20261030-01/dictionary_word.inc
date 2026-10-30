	/* Preserve forward LZ repetition. A scalar word is safe only when it
	 * cannot consume bytes that this same word has yet to produce. Builtins
	 * use fixed eight-byte copies, legal under the existing no-SIMD flags.
	 * Dictionary wrapping is handled before each word, as in the byte path.
	 */
	if (dist == 0 && left >= 8) {
		uint64_t word = (uint64_t)dict->buf[back] * 0x0101010101010101ULL;
		do {
			__builtin_memcpy(dict->buf + dict->pos, &word, 8);
			dict->pos += 8;
			left -= 8;
		} while (left >= 8);
		back = dict->pos - 1;
	} else if (dist >= 7) {
		while (left >= 8) {
			if (dict->end - back < 8) {
				dict->buf[dict->pos++] = dict->buf[back++];
				if (back == dict->end)
					back = 0;
				--left;
			} else {
				uint64_t word;
				__builtin_memcpy(&word, dict->buf + back, 8);
				__builtin_memcpy(dict->buf + dict->pos, &word, 8);
				dict->pos += 8;
				back += 8;
				left -= 8;
				if (back == dict->end)
					back = 0;
			}
		}
	}
	while (left > 0) {
		dict->buf[dict->pos++] = dict->buf[back++];
		if (back == dict->end)
			back = 0;
		--left;
	}
