# Domino Interview Project: domino-somascan-pipeline

## Background

SomaScan data requires a multistep normalization pipeline that works well within a
Domino Flow. This repo defines a `preprocess-somascan-data` which can be used as the
first step in a larger SomaScan project that starts from `.adat` input. The pipeline
used is a python implementation of the one defined across 3 papers:

- [Assessment of Variability in the SOMAscan Assay](https://www.nature.com/articles/s41598-017-14755-5)
- [Assessment of variability in the plasma 7k SomaScan proteomics assay](https://www.nature.com/articles/s41598-022-22116-0)
- [SomaScan Bioinformatics: Normalization, Quality Control, and Assessment of Pre-Analytical Variation](https://www.biorxiv.org/content/10.1101/2024.02.09.579724v1.full)

## Use

Launch the workflow against a specific input file:

```bash
make run-pipeline INPUT=<name-of-adat-file> [SOURCE=raw]
```

`pyflyte` requires a configured Flyte/Domino remote, so `run-pipeline` will only work from an
environment with that access. The pipeline runs against the currently checked-out git branch (via
`MainRepoGitRef`), so any new or changed pipeline step must be committed/pushed on the active branch before
a remote run will pick it up.

### Source datasets

`input_file` is a file inside a Domino dataset and the workflow's first step (`Convert ADAT to CSVs`) mounts
a snapshot of that dataset and reads the `.adat` file from it. Which dataset gets mounted is controlled separately
with the `SOURCE` variable:

- The `SOURCE` make variable (defaults to `raw`) sets the `PREPROCESS_SOMASCAN_DATA_SOURCE` environment
  variable, which `workflow.py` reads to pick the Domino dataset by name.
- To run against a different dataset, pass `SOURCE=<dataset-name>`:

  ```bash
  make run-pipeline SOURCE=my-other-dataset INPUT=<adat-file-in-that-dataset>
  ```

The dataset must already have at least one snapshot taken after data upload. The workflow looks up the named
dataset via the Domino API, and raises `DeployError` if it can't find a dataset with that name, or if it has
not had a snapshot created. When present, it always runs against the **latest** snapshot of that dataset,
so re-snapshotting a dataset and re-running the pipeline (with the same `SOURCE`/`INPUT`) is how you pick up
newly uploaded source data.

## Testing

Run the test suite (via Docker Compose, so it matches the pipeline's execution environment):

```bash
make test-local
```

Run a single test:

```bash
docker-compose run --rm app python -m pytest preprocess-somascan-data/tests/test_normalization.py::test_calibrators_normalized_by_hce
```
