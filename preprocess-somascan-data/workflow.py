import os
import pathlib
import subprocess

from flytekit import workflow
from flytekitplugins.domino.task import DominoJobConfig, DominoJobTask, GitRef


WORKFLOW_PATH = pathlib.Path(__file__).parent.resolve()


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
            MainRepoGitRef = GitRef(Type="branches", Value=get_current_branch())
        ),
        inputs={'input_file': str},
        outputs={
            'samples': str,
            'features': str,
            'measurements': str
        },
        use_latest=True
    )
    samples, features, measurements_raw = adat_to_csvs(input_file=input_file)

    return measurements_raw
