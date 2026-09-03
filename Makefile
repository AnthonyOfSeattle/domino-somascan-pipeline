SOURCE ?= raw

run-pipeline:
	@if [ -z "$(INPUT)" ]; then echo "INPUT is required, e.g. make run-pipeline INPUT=SS-217041.raw.adat"; exit 1; fi
	PREPROCESS_SOMASCAN_DATA_SOURCE=$(SOURCE) pyflyte run --remote preprocess-somascan-data/workflow.py preprocess_somascan_data \
		--input_file $(INPUT)

run-pipeline-test:
	$(MAKE) run-pipeline SOURCE=raw INPUT=SS-217041.raw.adat

test-local:
	docker-compose run --rm app python -m pytest preprocess-somascan-data
