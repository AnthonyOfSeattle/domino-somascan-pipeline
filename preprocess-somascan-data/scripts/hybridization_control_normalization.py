import pandas as pd

TYPE_HCE = "Hybridization Control Elution"


def normalize_by_hce(
    measurements: pd.DataFrame,
    samples: pd.DataFrame,
    features: pd.DataFrame
) -> pd.DataFrame:

    # 1. Identify HCE features
    features_hce = features.loc[
        features["Type"] == TYPE_HCE
    ]
    
    # 2. Subset to HCE measurements
    measurements_hce = (
        features_hce["ProbeId"]
                    .to_frame()
                    .join(
                        measurements.set_index("ProbeId"),
                        on = "ProbeId"
                    )
    )
    
    # 3. Calculate HCE reference value
    measurements_hce_ref = (
        measurements_hce.groupby(["PlateId", "ProbeId"])
                         .value
                         .median()
                         .rename("value_ref")
    )
    
    # 4. Calculate the scale factor
    measurements_hce_scale_factor = measurements_hce.join(
        measurements_hce_ref,
        on = ["PlateId", "ProbeId"]
    )
    measurements_hce_scale_factor["value_scale_factor"] = (
        measurements_hce_scale_factor.value_ref /
           measurements_hce_scale_factor.value
    )
    measurements_hce_scale_factor = (
        measurements_hce_scale_factor.groupby(["PlateId", "PlatePosition"])
                                 .value_scale_factor
                                 .median()
    )
    
    # 5. Apply scale factor
    measurements_hcn = measurements.join(
        measurements_hce_scale_factor,
        on = ["PlateId", "PlatePosition"]
    )
    measurements_hcn.value *= measurements_hcn.value_scale_factor
    measurements_hcn = measurements_hcn.drop("value_scale_factor", axis = 1)

    return measurements_hcn


if __name__ == "__main__":
    # 1. Read input
    features = pd.read_csv("/workflow/outputs/features.csv", index=False)
    samples = pd.read_csv("/workflow/outputs/samples.csv", index=False)
    measurements = pd.read_csv("/workflow/outputs/measurements.csv", index=False)

    # 2. Normalize data
    measurements_processed = normalize_by_hce(measurements, samples, features)

    # 3. Write workflow output
    measurements_processed.to_csv(
        "/workflow/outputs/measurements.hybridization_control_normalized.csv",
        index=False
    )
