run-pipeline-test:
	pyflyte run --remote preprocess-somascan-data/workflow.py preprocess_somascan_data \
		--input_file /mnt/data/raw/SS-217041.raw.adat
