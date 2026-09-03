import os
import pandas as pd
import somadata as sd

from pathlib import Path

class SomaScanData:
    def __init__(self):
        self.features = None
        self.samples = None
        self.measurements = None

def parse_adat(input_file: str) -> SomaScanData:
    data = SomaScanData()

    adat = sd.read_adat(input_file)
    data.features = adat.columns.to_frame(index=False).rename({"SeqId": "ProbeId"}, axis = 1)
    data.samples = adat.index.to_frame().reset_index(drop = True)
    data.measurements = adat.reset_index(drop = True)
    data.measurements.columns = data.features["ProbeId"]
    data.measurements = pd.concat(
        [
            data.samples.loc[:, ["PlateId", "PlatePosition"]],
            data.measurements
        ],
        axis=1
    )
    data.measurements = data.measurements.melt(
        id_vars=["PlateId", "PlatePosition"],
        var_name="ProbeId"
    )

    return data

if __name__ == "__main__":
    # 1. Read inputs
    input_file = Path("/workflow/inputs/input_file").read_text().strip()
    source_dataset = Path("/workflow/inputs/source_dataset").read_text().strip()

    # 2. Resolve the file within the source dataset mount
    dataset_dir = Path("/mnt/data") / source_dataset
    resolved_file = dataset_dir / Path(input_file).name
    if not resolved_file.exists():
        raise FileNotFoundError(
            f"Could not find '{resolved_file.name}' in dataset '{source_dataset}' at {dataset_dir}"
        )

    # 3. Parse data
    data = parse_adat(str(resolved_file))

    # 4. Write workflow outputs
    data.features.to_csv("/workflow/outputs/features.csv", index=False)
    data.samples.to_csv("/workflow/outputs/samples.csv", index=False)
    data.measurements.to_csv("/workflow/outputs/measurements.csv", index=False)
