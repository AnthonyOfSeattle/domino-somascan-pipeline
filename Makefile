run-pipeline-test:
	pyflyte run --remote preprocess-somascan-data/workflow.py preprocess_somascan_data \
		--input_file /mnt/data/raw/SS-217041.raw.adat

test-local:
	docker-compose run --rm app python -m pytest preprocess-somascan-data
