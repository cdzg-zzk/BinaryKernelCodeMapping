SUBDIRS := \
	layer1/01_data_independent \
	layer1/02_data_dependent \
	layer1/03_func_stable \
	layer1/04_func_entropy \
	layer2/01_func_placement \
	layer3/01_sha256_transform \
	layer3/02_bch_encode \
	layer3/03_zlib_deflate \
	layer3/04_zstd_decompress \
	layer3/05_crc32_le \
	layer3/06_lz4_compress_fast \
	layer3/07_aes_encrypt \
	layer3/08_lz4_decompress_safe \
	layer3/09_hex_dump_to_buffer \
	layer3/10_string_escape_mem

all:
	@for d in $(SUBDIRS); do \
		echo "==> $$d"; \
		$(MAKE) -C $$d all || exit $$?; \
	done

run:
	./run_experiment.sh all

clean:
	@for d in $(SUBDIRS); do \
		$(MAKE) -C $$d clean; \
	done
	rm -rf results

.PHONY: all run clean
