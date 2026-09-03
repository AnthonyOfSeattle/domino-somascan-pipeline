# preprocess-somascan-data

Flyte workflow definition and pipeline step scripts for preprocessing SomaScan proteomics data. See the
[repo-level README](../README.md) for how to test and launch this pipeline.

## Workflow architecture

The workflow (`workflow.py`, `preprocess_somascan_data`) takes a raw `.adat` file and a Domino dataset
snapshot it was uploaded to, and runs a linear sequence of `DominoJobTask` steps, each executing one script
in `scripts/` as a standalone Domino job. Flyte passes data between steps as files (`FlyteFile`), not
in-process Python objects, and each step is committed to its own Domino artifact:

- **Converted Data** (`CONVERTED_DATA_ARTIFACT`, type `DATA`) — the intermediate `samples`/`features`/
  `measurements` CSVs produced and refined by each conversion/normalization step.
- **QC Report** (`QC_ARTIFACT`, type `REPORT`) — PCA and calibrator-CV plots, generated once from the raw
  data and once from the fully normalized data.
- **Final Dataset** (`FINAL_DATASET_ARTIFACT`, type `DATA`) — the subsampled, analysis-ready output.

### Data model

Three tables flow through every step:

- **`features`** — one row per probe/analyte, keyed by `ProbeId`. Carries `Type` (e.g.
  `Hybridization Control Elution`, `Protein`) and `Organism`.
- **`samples`** — one row per plate/well, keyed by `PlateId`/`PlatePosition`. Carries `SampleType` (e.g.
  `Calibrator`, `Sample`, buffer/QC wells).
- **`measurements`** — long/melted format, one row per `PlateId`/`PlatePosition`/`ProbeId` with a `value`
  column.

Each normalization step joins `measurements` against `features` and/or `samples` to select the relevant
probes/samples, computes a per-plate (and/or per-probe) reference value and scale factor, and applies it to
`value`, producing a new `measurements_*` CSV that feeds the next step. `samples` and `features` pass
through unchanged until `finalize_dataset.py`.

### Steps

1. **Convert ADAT to CSVs** (`scripts/adat_to_csvs.py`, `parse_adat`) — reads the `.adat` file (via
   `somadata`) and the source dataset snapshot, and emits the initial `samples`/`features`/`measurements`
   CSVs.
2. **QC report (raw)** (`scripts/qc_report.py`) — PCA and calibrator-CV plots on the freshly converted data,
   for comparison against the final report.
3. **Hybridization control normalization** (`scripts/hybridization_control_normalization.py`,
   `normalize_by_hce`) — scales each plate's measurements so its Hybridization Control Elution (HCE) probes
   match their per-plate/probe median.
4. **Median signal normalization on calibrators** (`scripts/median_signal_normalization_calibrators.py`,
   `normalize_by_msn_calibrators`) — scales calibrator-well measurements (excluding HCE probes) to their
   per-plate/probe median.
5. **Plate-scale normalization** (`scripts/plate_scale_normalization.py`, `normalize_by_plate_scale`) —
   scales each plate's calibrator measurements to a single cross-plate per-probe reference value.
6. **Interplate calibration** (`scripts/interplate_calibration.py`, `normalize_by_interplate_calibration`) —
   a second cross-plate calibrator-based scale factor, applied per plate/probe.
7. **Median signal normalization on all sample types** (`scripts/median_signal_normalization_all.py`,
   `normalize_by_msn_all`) — scales measurements (excluding HCE probes) to a per-sample-type/probe median,
   so different sample types (calibrators, samples, buffers, QC) are normalized independently.
8. **Finalize dataset** (`scripts/finalize_dataset.py`, `finalize_dataset`) — subsets the fully normalized
   tables to `features.Type == "Protein"` and `features.Organism == "Human"`, and to
   `samples.SampleType == "Sample"` (dropping calibrators, buffers, and QC wells), writing the result into
   the `Final Dataset` artifact.
9. **QC report (final)** (`scripts/qc_report.py`) — the same PCA/calibrator-CV plots, run again on the fully
   normalized data, for comparison against step 2.

Steps 3–7 chain the `measurements` output of one step into the `measurements` input of the next, while
`samples`/`features` are threaded through from step 1 unchanged.

### Adding a new step

Each script exposes a plain, testable function that operates on in-memory `pandas.DataFrame`s, plus an
`if __name__ == "__main__":` block that adapts it to the Domino job I/O convention: inputs are read from
`/workflow/inputs/<name>`, outputs are written to `/workflow/outputs/<name>`. Follow this same split
(importable function + thin CLI shim) so the logic stays unit-testable, then wire the script into
`workflow.py` as a new `DominoJobTask`. `MainRepoGitRef` is set from the currently checked-out git branch, so
a new step must be committed/pushed on the active branch before a remote run will pick it up.
