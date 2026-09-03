import os
import pathlib
import subprocess
from typing import TypeVar

from domino import Domino
from flytekit import workflow
from flytekit.types.file import FlyteFile
from flytekitplugins.domino.task import DatasetSnapshot, DominoJobConfig, DominoJobTask, GitRef
from flytekitplugins.domino.artifact import Artifact, DATA, REPORT


WORKFLOW_PATH = pathlib.Path(__file__).parent.resolve()
SOURCE_DATASET_NAME = "raw"

CONVERTED_DATA_ARTIFACT = Artifact(name="Converted Data", type=DATA)
QC_ARTIFACT = Artifact(name="QC Report", type=REPORT)
FINAL_DATASET_ARTIFACT = Artifact(name="Final Dataset", type=DATA)


class DeployError(Exception):
    pass


def get_current_branch():
    try:
        # Runs the git command to get the active branch name
        branch = subprocess.check_output(
            ["git", "branch", "--show-current"], 
            stderr=subprocess.DEVNULL
        ).decode("utf-8").strip()
        
        return branch if branch else "Detached HEAD"
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def get_source_dataset_snapshot():
    domino = Domino(
        os.path.join(
            os.environ["DOMINO_USER_NAME"],
            os.environ["DOMINO_PROJECT_NAME"]
        )
    )
    datasets = [
        d for d in domino.datasets_list(os.environ["DOMINO_PROJECT_ID"])
        if d["datasetName"] == SOURCE_DATASET_NAME
    ]
    if not datasets:
        raise DeployError(f"No dataset present named '{SOURCE_DATASET_NAME}'")

    dataset_details = domino.datasets_details(datasets[0]["datasetId"])
    if len(dataset_details["snapshots"]) == 1:
        raise DeployError(f"You must make a snapshot of dataset '{SOURCE_DATASET_NAME}'")

    dataset_snapshot = DatasetSnapshot(
        Id = dataset_details["datasetId"],
        Version = len(dataset_details["snapshots"]) - 1
    )
    return dataset_snapshot


@workflow
def preprocess_somascan_data(input_file: str) -> str:

    # 1. Convert adat file
    adat_to_csvs = DominoJobTask(
        name='Convert ADAT to CSVs',
        domino_job_config=DominoJobConfig(
            Command="python " + os.path.join(WORKFLOW_PATH, "scripts", "adat_to_csvs.py"),
            MainRepoGitRef = GitRef(Type="branches", Value=get_current_branch()),
            DatasetSnapshots = [get_source_dataset_snapshot()],
            HardwareTierId = "small-k8s"
        ),
        inputs={'input_file': str},
        outputs={
            'samples': CONVERTED_DATA_ARTIFACT.File(name="samples.csv"),
            'features': CONVERTED_DATA_ARTIFACT.File(name="features.csv"),
            'measurements': CONVERTED_DATA_ARTIFACT.File(name="measurements.csv")
        },
        use_latest=True
    )
    samples, features, measurements = adat_to_csvs(input_file=input_file)

    # 1b. QC report on the freshly converted data
    qc_report_raw = DominoJobTask(
        name='QC report (raw)',
        domino_job_config=DominoJobConfig(
            Command="python " + os.path.join(WORKFLOW_PATH, "scripts", "qc_report.py"),
            MainRepoGitRef = GitRef(Type="branches", Value=get_current_branch()),
            HardwareTierId = "medium-k8s"
        ),
        inputs={
            "stage": str,
            "measurements": FlyteFile[TypeVar("csv")],
            "samples": FlyteFile[TypeVar("csv")],
            "features": FlyteFile[TypeVar("csv")]
        },
        outputs={
            'pca_raw': QC_ARTIFACT.File(name="pca_raw.png"),
            'cv_raw': QC_ARTIFACT.File(name="cv_raw.png")
        },
        use_latest=True
    )
    qc_report_raw(
        stage="raw",
        measurements = measurements,
        samples = samples,
        features = features
    )

    # 2. Hybridization control normalization
    normalize_by_hce = DominoJobTask(
        name='Hybridization control normalization',
        domino_job_config=DominoJobConfig(
            Command="python " + os.path.join(WORKFLOW_PATH, "scripts", "hybridization_control_normalization.py"),
            MainRepoGitRef = GitRef(Type="branches", Value=get_current_branch()),
            HardwareTierId = "medium-k8s"
        ),
        inputs={
            "measurements": FlyteFile[TypeVar("csv")],
            "samples": FlyteFile[TypeVar("csv")],
            "features": FlyteFile[TypeVar("csv")]
        },
        outputs={
            'measurements_hcn': CONVERTED_DATA_ARTIFACT.File(name="measurements_hcn.csv")
        },
        use_latest=True
    )
    data_hcn = normalize_by_hce(
        measurements = measurements,
        samples = samples,
        features = features
    )

    # 3. Median signal normalization on calibrators
    normalize_by_msn_calibrators = DominoJobTask(
        name='Median signal normalization on calibrators',
        domino_job_config=DominoJobConfig(
            Command="python " + os.path.join(WORKFLOW_PATH, "scripts", "median_signal_normalization_calibrators.py"),
            MainRepoGitRef = GitRef(Type="branches", Value=get_current_branch()),
            HardwareTierId = "medium-k8s"
        ),
        inputs={
            "measurements": FlyteFile[TypeVar("csv")],
            "samples": FlyteFile[TypeVar("csv")],
            "features": FlyteFile[TypeVar("csv")]
        },
        outputs={
            'measurements_msncal': CONVERTED_DATA_ARTIFACT.File(name="measurements_msncal.csv")
        },
        use_latest=True
    )
    data_msncal = normalize_by_msn_calibrators(
        measurements = data_hcn,
        samples = samples,
        features = features
    )

    # 4. Plate-scale normalization
    normalize_by_plate_scale = DominoJobTask(
        name='Plate-scale normalization',
        domino_job_config=DominoJobConfig(
            Command="python " + os.path.join(WORKFLOW_PATH, "scripts", "plate_scale_normalization.py"),
            MainRepoGitRef = GitRef(Type="branches", Value=get_current_branch()),
            HardwareTierId = "medium-k8s"
        ),
        inputs={
            "measurements": FlyteFile[TypeVar("csv")],
            "samples": FlyteFile[TypeVar("csv")],
            "features": FlyteFile[TypeVar("csv")]
        },
        outputs={
            'measurements_psn': CONVERTED_DATA_ARTIFACT.File(name="measurements_psn.csv")
        },
        use_latest=True
    )
    data_psn = normalize_by_plate_scale(
        measurements = data_msncal,
        samples = samples,
        features = features
    )

    # 5. Inter-plate calibration
    normalize_by_interplate_calibration = DominoJobTask(
        name='Interplate calibration',
        domino_job_config=DominoJobConfig(
            Command="python " + os.path.join(WORKFLOW_PATH, "scripts", "interplate_calibration.py"),
            MainRepoGitRef = GitRef(Type="branches", Value=get_current_branch()),
            HardwareTierId = "medium-k8s"
        ),
        inputs={
            "measurements": FlyteFile[TypeVar("csv")],
            "samples": FlyteFile[TypeVar("csv")],
            "features": FlyteFile[TypeVar("csv")]
        },
        outputs={
            'measurements_ipc': CONVERTED_DATA_ARTIFACT.File(name="measurements_ipc.csv")
        },
        use_latest=True
    )
    data_ipc = normalize_by_interplate_calibration(
        measurements = data_psn,
        samples = samples,
        features = features
    )

    # 6. Median signal normalization on all sample types
    normalize_by_msn_all = DominoJobTask(
        name='Median signal normalization on all sample types',
        domino_job_config=DominoJobConfig(
            Command="python " + os.path.join(WORKFLOW_PATH, "scripts", "median_signal_normalization_all.py"),
            MainRepoGitRef = GitRef(Type="branches", Value=get_current_branch()),
            HardwareTierId = "medium-k8s"
        ),
        inputs={
            "measurements": FlyteFile[TypeVar("csv")],
            "samples": FlyteFile[TypeVar("csv")],
            "features": FlyteFile[TypeVar("csv")]
        },
        outputs={
            'measurements_msnall': CONVERTED_DATA_ARTIFACT.File(name="measurements_msnall.csv")
        },
        use_latest=True
    )
    data_msnall = normalize_by_msn_all(
        measurements = data_ipc,
        samples = samples,
        features = features
    )

    # 7. Finalize dataset
    finalize_dataset = DominoJobTask(
        name='Finalize dataset',
        domino_job_config=DominoJobConfig(
            Command="python " + os.path.join(WORKFLOW_PATH, "scripts", "finalize_dataset.py"),
            MainRepoGitRef = GitRef(Type="branches", Value=get_current_branch()),
            HardwareTierId = "medium-k8s"
        ),
        inputs={
            "measurements": FlyteFile[TypeVar("csv")],
            "samples": FlyteFile[TypeVar("csv")],
            "features": FlyteFile[TypeVar("csv")]
        },
        outputs={
            'samples_final': FINAL_DATASET_ARTIFACT.File(name="samples_final.csv"),
            'features_final': FINAL_DATASET_ARTIFACT.File(name="features_final.csv"),
            'measurements_final': FINAL_DATASET_ARTIFACT.File(name="measurements_final.csv")
        },
        use_latest=True
    )
    finalize_dataset(
        measurements = data_msnall,
        samples = samples,
        features = features
    )

    # 8. QC report on the fully normalized data
    qc_report_final = DominoJobTask(
        name='QC report (final)',
        domino_job_config=DominoJobConfig(
            Command="python " + os.path.join(WORKFLOW_PATH, "scripts", "qc_report.py"),
            MainRepoGitRef = GitRef(Type="branches", Value=get_current_branch()),
            HardwareTierId = "medium-k8s"
        ),
        inputs={
            "stage": str,
            "measurements": FlyteFile[TypeVar("csv")],
            "samples": FlyteFile[TypeVar("csv")],
            "features": FlyteFile[TypeVar("csv")]
        },
        outputs={
            'pca_final': QC_ARTIFACT.File(name="pca_final.png"),
            'cv_final': QC_ARTIFACT.File(name="cv_final.png")
        },
        use_latest=True
    )
    qc_report_final(
        stage="final",
        measurements = data_msnall,
        samples = samples,
        features = features
    )

    return "SUCCESS"
