import pandas as pd

TYPE_HCE = "Hybridization Control Elution"


def normalize_by_msn_all(
    measurements: pd.DataFrame,
    samples: pd.DataFrame,
    features: pd.DataFrame
) -> pd.DataFrame:

    # 1. Annotate measurements with sample type
    measurements_annotated = (
        measurements.join(
                        samples.set_index(["PlateId", "PlatePosition"]).SampleType,
                        on = ["PlateId", "PlatePosition"]
                    )
    )

    # 2. Exclude HCE probes from the scale factor calculation
    features_hce = features.loc[
        features["Type"] == TYPE_HCE
    ]
    measurements_annotated = measurements_annotated[
        ~measurements_annotated.ProbeId.isin(features_hce.ProbeId)
    ]

    # 3. Calculate per-sample-type/probe reference value
    measurements_msnall_ref = (
        measurements_annotated.groupby(["SampleType", "ProbeId"])
                              .value
                              .median()
                              .rename("value_ref")
    )

    # 4. Calculate the scale factor per plate/well/dilution
    measurements_msnall_scale_factor = measurements_annotated.join(
        measurements_msnall_ref,
        on = ["SampleType", "ProbeId"]
    )
    measurements_msnall_scale_factor["value_ratio"] = (
        measurements_msnall_scale_factor.value /
            measurements_msnall_scale_factor.value_ref
    )
    measurements_msnall_scale_factor = (
        1 / measurements_msnall_scale_factor.join(
                                                features.set_index("ProbeId")["Dilution"],
                                                     on = "ProbeId"
                                                ).groupby(["PlateId", "PlatePosition", "Dilution"])
                                                .value_ratio
                                                .median()
                                                .rename("value_scale_factor")
    )

    # 5. Apply scale factor
    measurements_msnall = (
        measurements.join(
                        features.set_index("ProbeId")["Dilution"],
                        on = "ProbeId"
                     ).join(
                         measurements_msnall_scale_factor,
                         on = ["PlateId", "PlatePosition", "Dilution"]
                     )
    )
    measurements_msnall.loc[~measurements_msnall["value_scale_factor"].isna(), "value"] *= (
        measurements_msnall.loc[~measurements_msnall["value_scale_factor"].isna(), "value_scale_factor"]
    )
    measurements_msnall = measurements_msnall.drop(["Dilution", "value_scale_factor"], axis = 1)

    return measurements_msnall


if __name__ == "__main__":
    # 1. Read input
    measurements = pd.read_csv("/workflow/inputs/measurements")
    samples = pd.read_csv("/workflow/inputs/samples")
    features = pd.read_csv("/workflow/inputs/features")

    # 2. Normalize data
    measurements_processed = normalize_by_msn_all(measurements, samples, features)

    # 3. Write workflow output
    measurements_processed.to_csv(
        "/workflow/outputs/measurements_msnall.csv",
        index=False
    )
