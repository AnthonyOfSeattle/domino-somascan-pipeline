import os
import pathlib
import subprocess
from typing import TypeVar

from flytekit import workflow
from flytekit.types.file import FlyteFile
from flytekitplugins.domino.task import DatasetSnapshot, DominoJobConfig, DominoJobTask, GitRef
from flytekitplugins.domino.artifact import Artifact, DATA, MODEL, REPORT


WORKFLOW_PATH = pathlib.Path(__file__).parent.resolve()
CONVERTED_DATA_ARTIFACT = Artifact(name="Converted Data", type=DATA)


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


@workflow
def preprocess_somascan_data(input_file: str) -> str:

    # 1. Convert adat file
    adat_to_csvs = DominoJobTask(
        name='Convert ADAT to CSVs',
        domino_job_config=DominoJobConfig(
            Command="python " + os.path.join(WORKFLOW_PATH, "scripts", "adat_to_csvs.py"),
            MainRepoGitRef = GitRef(Type="branches", Value=get_current_branch()),
            DatasetSnapshots = [DatasetSnapshot(Id="6a90998054fe9d26cb55e343", Version=1)],
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

    # 2. Hybridization control normalization
    normalize_by_hce = DominoJobTask(
        name='Hybridization control normalization',
        domino_job_config=DominoJobConfig(
            Command="python " + os.path.join(WORKFLOW_PATH, "scripts", "hybridization_control_normalization.py"),
            MainRepoGitRef = GitRef(Type="branches", Value=get_current_branch()),
            DatasetSnapshots = [DatasetSnapshot(Id="6a90998054fe9d26cb55e343", Version=1)],
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
            DatasetSnapshots = [DatasetSnapshot(Id="6a90998054fe9d26cb55e343", Version=1)],
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
            DatasetSnapshots = [DatasetSnapshot(Id="6a90998054fe9d26cb55e343", Version=1)],
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
            DatasetSnapshots = [DatasetSnapshot(Id="6a90998054fe9d26cb55e343", Version=1)],
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

    return "SUCCESS"
