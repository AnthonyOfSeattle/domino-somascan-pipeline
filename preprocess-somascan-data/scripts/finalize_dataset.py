import pandas as pd

from typing import Tuple

TYPE_PROTEIN = "Protein"
ORGANISM_HUMAN = "Human"
SAMPLE_TYPE_SAMPLE = "Sample"


def finalize_dataset(
    measurements: pd.DataFrame,
    samples: pd.DataFrame,
    features: pd.DataFrame
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:

    # 1. Subsample to human protein features and sample wells
    features_final = features.loc[
        (features["Type"] == TYPE_PROTEIN) & (features["Organism"] == ORGANISM_HUMAN)
    ]
    samples_final = samples.loc[samples["SampleType"] == SAMPLE_TYPE_SAMPLE]

    # 2. Subsample measurements to match
    measurements_final = measurements.merge(
        samples_final[["PlateId", "PlatePosition"]],
        how="inner"
    ).merge(
        features_final["ProbeId"],
        how="inner"
    )

    return samples_final, features_final, measurements_final


if __name__ == "__main__":
    # 1. Read input
    measurements = pd.read_csv("/workflow/inputs/measurements")
    samples = pd.read_csv("/workflow/inputs/samples")
    features = pd.read_csv("/workflow/inputs/features")

    # 2. Finalize dataset
    samples_final, features_final, measurements_final = finalize_dataset(
        measurements, samples, features
    )

    # 3. Write workflow outputs
    samples_final.to_csv("/workflow/outputs/samples_final.csv", index=False)
    features_final.to_csv("/workflow/outputs/features_final.csv", index=False)
    measurements_final.to_csv("/workflow/outputs/measurements_final.csv", index=False)
