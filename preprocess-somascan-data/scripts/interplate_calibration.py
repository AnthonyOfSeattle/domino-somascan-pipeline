import pandas as pd

TYPE_CALIBRATOR = "Calibrator"


def normalize_by_interplate_calibration(
    measurements: pd.DataFrame,
    samples: pd.DataFrame,
    features: pd.DataFrame
) -> pd.DataFrame:

    # 1. Identify calibrator samples
    samples_calibrators = samples.loc[
        samples["SampleType"] == TYPE_CALIBRATOR
    ]

    # 2. Subset to calibrator measurements
    measurements_calibrators = (
        samples_calibrators.loc[:, ["PlateId", "PlatePosition"]]
                           .join(
                               measurements.set_index(["PlateId", "PlatePosition"]),
                               on = ["PlateId", "PlatePosition"]
                           )
    )

    # 3. Calculate cross-plate reference value per probe
    measurements_interplate_ref = (
        measurements_calibrators.groupby(["ProbeId"])
                                .value
                                .median()
                                .rename("value_ref")
    )

    # 4. Calculate the scale factor per plate/probe
    measurements_interplate_scale_factor = (
        measurements_calibrators.groupby(["PlateId", "ProbeId"])
                                .value
                                .median()
                                .to_frame()
                                .reset_index()
                                .join(
                                    measurements_interplate_ref,
                                    on = ["ProbeId"]
                                )
    )
    measurements_interplate_scale_factor["value_scale_factor"] = (
        measurements_interplate_scale_factor.value_ref /
           measurements_interplate_scale_factor.value
    )
    measurements_interplate_scale_factor = (
        measurements_interplate_scale_factor.set_index(["PlateId", "ProbeId"])
                                            .value_scale_factor
    )

    # 5. Apply scale factor
    measurements_ipc = (
        measurements.join(
                        measurements_interplate_scale_factor,
                        on = ["PlateId", "ProbeId"]
                    )
    )
    measurements_ipc.value *= measurements_ipc.value_scale_factor
    measurements_ipc = measurements_ipc.drop(["value_scale_factor"], axis = 1)

    return measurements_ipc


if __name__ == "__main__":
    # 1. Read input
    measurements = pd.read_csv("/workflow/inputs/measurements")
    samples = pd.read_csv("/workflow/inputs/samples")
    features = pd.read_csv("/workflow/inputs/features")

    # 2. Normalize data
    measurements_processed = normalize_by_interplate_calibration(measurements, samples, features)

    # 3. Write workflow output
    measurements_processed.to_csv(
        "/workflow/outputs/measurements_ipc.csv",
        index=False
    )
