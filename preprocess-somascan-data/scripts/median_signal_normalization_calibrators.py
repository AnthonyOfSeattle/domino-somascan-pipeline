import pandas as pd

TYPE_CALIBRATOR = "Calibrator"
TYPE_HCE = "Hybridization Control Elution"


def normalize_by_msn_calibrators(
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

    # 3. Exclude HCE probes from the scale factor calculation
    features_non_hce = features.loc[
        features["Type"] != TYPE_HCE
    ]
    measurements_calibrators = (
        features_non_hce["ProbeId"]
                        .to_frame()
                        .join(
                            measurements_calibrators.set_index("ProbeId"),
                            on = "ProbeId"
                        )
    )

    # 4. Calculate per-plate/probe reference value
    measurements_calibrators_ref = (
        measurements_calibrators.groupby(["PlateId", "ProbeId"])
                                .value
                                .median()
                                .rename("value_ref")
    )

    # 5. Calculate the scale factor per plate/well/dilution
    measurements_calibrators_scale_factor = measurements_calibrators.join(
        measurements_calibrators_ref,
        on = ["PlateId", "ProbeId"]
    )
    measurements_calibrators_scale_factor["value_ratio"] = (
        measurements_calibrators_scale_factor.value /
            measurements_calibrators_scale_factor.value_ref
    )
    measurements_calibrators_scale_factor = (
        1 / measurements_calibrators_scale_factor.join(
                                                     features.set_index("ProbeId")["Dilution"],
                                                     on = "ProbeId"
                                                  ).groupby(["PlateId", "PlatePosition", "Dilution"])
                                                  .value_ratio
                                                  .median()
                                                  .rename("value_scale_factor")
    )

    # 6. Apply scale factor
    measurements_msncal = (
        measurements.join(
                        features.set_index("ProbeId")["Dilution"],
                        on = "ProbeId"
                     ).join(
                         measurements_calibrators_scale_factor,
                         on = ["PlateId", "PlatePosition", "Dilution"]
                     )
    )
    measurements_msncal.loc[~measurements_msncal["value_scale_factor"].isna(), "value"] *= (
        measurements_msncal.loc[~measurements_msncal["value_scale_factor"].isna(), "value_scale_factor"]
    )
    measurements_msncal = measurements_msncal.drop(["Dilution", "value_scale_factor"], axis = 1)

    return measurements_msncal


if __name__ == "__main__":
    # 1. Read input
    measurements = pd.read_csv("/workflow/inputs/measurements")
    samples = pd.read_csv("/workflow/inputs/samples")
    features = pd.read_csv("/workflow/inputs/features")

    # 2. Normalize data
    measurements_processed = normalize_by_msn_calibrators(measurements, samples, features)

    # 3. Write workflow output
    measurements_processed.to_csv(
        "/workflow/outputs/measurements_msncal.csv",
        index=False
    )
