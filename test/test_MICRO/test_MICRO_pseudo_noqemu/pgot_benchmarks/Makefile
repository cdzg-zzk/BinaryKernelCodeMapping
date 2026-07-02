SUBDIRS := \
	layer1/01_data_independent \
	layer1/02_data_dependent \
	layer1/03_func_stable \
	layer1/04_func_entropy \
	layer2/01_density_data \
	layer2/02_density_func

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
