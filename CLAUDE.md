# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

This repo defines a Flyte/Domino data pipeline that preprocesses SomaScan proteomics data. It reads a
proprietary `.adat` file (via the `somadata` package), converts it into tabular CSVs, and applies
normalization steps (currently hybridization control normalization). The pipeline is orchestrated as a
Flyte workflow (`flytekit`) whose individual steps run as Domino jobs (`flytekitplugins.domino`).

## Commands

Run from the `preprocess-somascan-data/` directory (its scripts import each other as
`from scripts import <module>`, and tests as `from scripts import ...` too, so both scripts and pytest
must be invoked with that directory as the working directory):

```bash
cd preprocess-somascan-data
python -m pytest tests/            # run all tests
python -m pytest tests/test_normalization.py::test_calibrators_normalized_by_hce  # run a single test
```

Install dependencies with `pip install -r requirements.txt` (currently just `SomaData`; `flytekit`/
`flytekitplugins-domino`/`pandas`/`pytest` are expected to already be present in the Domino execution
environment and are not pinned here).

Launch the full workflow remotely on Domino/Flyte:

```bash
make run-pipeline-test
```

This runs `pyflyte run --remote preprocess-somascan-data/workflow.py preprocess_somascan_data --input_file <path>`
against a fixed test `.adat` file. `pyflyte` requires a configured Flyte/Domino remote — this only works
from an environment with that access.

## Architecture

- **`preprocess-somascan-data/workflow.py`** — the Flyte `@workflow` definition (`preprocess_somascan_data`).
  Each pipeline step is a `DominoJobTask` that runs one of the scripts in `scripts/` as a standalone Domino
  job (not an in-process function call). Steps are wired together by declaring `inputs`/`outputs` as
  `FlyteFile`s and `Artifact` outputs; Flyte passes files between steps rather than Python objects.
  `MainRepoGitRef` is set from the currently checked-out git branch (via `get_current_branch()`), so a new
  pipeline step must be committed/pushed on the active branch before a remote run will pick it up.
- **`preprocess-somascan-data/scripts/`** — one module per pipeline step. Each module exposes a plain,
  testable function (e.g. `parse_adat`, `normalize_by_hce`) that operates on in-memory `pandas.DataFrame`s,
  plus an `if __name__ == "__main__":` block that adapts it to the Domino job I/O convention: inputs are
  read from `/workflow/inputs/<name>`, outputs are written to `/workflow/outputs/<name>`. When adding a new
  step, follow this same split (importable function + thin CLI shim) so the logic stays unit-testable.
- **QC reporting**: `scripts/qc_report.py` exposes `plot_sample_pca` and `plot_calibrator_cv`, which build a
  sample-level PCA scatter plot (protein probes, `Sample` wells) and a per-plate calibrator CV distribution
  plot from a `measurements`/`samples`/`features` triple. The workflow runs this script twice as
  `DominoJobTask`s — once on the raw output of `adat_to_csvs.py` and once on the fully normalized output of
  `median_signal_normalization_all.py` — writing all four PNGs into a shared `QC_ARTIFACT` (`REPORT` type)
  so the two stages can be compared. The `stage` input (`"raw"`/`"final"`) is only used to label plot titles
  and output filenames, matching the input/output file conventions of the other scripts.
- **Final dataset**: `scripts/finalize_dataset.py` exposes `finalize_dataset`, which subsamples the fully
  normalized `measurements`/`samples`/`features` triple to `features.Type == "Protein"` and
  `features.Organism == "Human"`, and to `samples.SampleType == "Sample"` (dropping calibrators, buffers,
  and QC wells). The workflow runs this as a `DominoJobTask` after
  `median_signal_normalization_all.py`, writing the filtered `samples.csv`/`features.csv`/`measurements.csv`
  into a dedicated `FINAL_DATASET_ARTIFACT` (`DATA` type), separate from the per-step `Converted Data`
  artifact used earlier in the pipeline.
- **Data model**: three tables flow through the pipeline — `features` (one row per probe/analyte, keyed by
  `ProbeId`), `samples` (one row per plate/well, keyed by `PlateId`/`PlatePosition`), and `measurements`
  (long/melted format, one row per `PlateId`/`PlatePosition`/`ProbeId` with a `value` column). Normalization
  steps join `measurements` against `features` and/or `samples` to identify relevant probes (e.g. by
  `features["Type"]`) and compute per-plate/per-well scale factors applied to `value`.
- **`preprocess-somascan-data/tests/`** — tests validate a normalization function against pre-computed
  expected output stored as gzipped parquet fixtures in `tests/data/`, comparing per-row relative error in
  parts-per-million (see `test_normalization.py`) rather than exact float equality.
- **`notebooks/`** — exploratory/prototype notebooks that precede and mirror the pipeline scripts (e.g.
  `2026_08_26_extract_data.ipynb` prototypes `adat_to_csvs.py`). Treat them as scratch/history, not
  something to keep in sync with the scripts.
