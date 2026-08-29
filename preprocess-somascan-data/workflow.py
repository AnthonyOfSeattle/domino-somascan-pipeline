import os
import pathlib
import subprocess

from flytekit import workflow
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
    converted_data = adat_to_csvs(input_file=input_file)

    return "SUCCESS"
