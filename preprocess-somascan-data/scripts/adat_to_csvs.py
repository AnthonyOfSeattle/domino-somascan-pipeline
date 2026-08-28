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
    # 1. Read input
    input_file = Path("/workflow/inputs/input_file").read_text()

    # 2. Parse data
    data = parse_adat(input_file)

    # 3. Dump data
    data.features.to_csv("/mnt/data/processed/features.csv", index=False)
    data.samples.to_csv("/mnt/data/processed/samples.csv", index=False)
    data.measurements.to_csv("/mnt/data/processed/samples.csv", index=False)

    # 4. Write workflow outputs
    Path("/workflow/outputs/features").write_text("/mnt/data/processed/features.csv")
    Path("/workflow/outputs/samples").write_text("/mnt/data/processed/samples.csv")
    Path("/workflow/outputs/measurements").write_text("/mnt/data/processed/measurements.csv")
