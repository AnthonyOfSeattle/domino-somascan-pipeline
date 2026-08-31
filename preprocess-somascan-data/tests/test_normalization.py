import os
import pandas as pd

from scripts import hybridization_control_normalization as hcn

TESTS_PATH = os.path.dirname(os.path.abspath(__file__))


def test_calibrators_normalized_by_hce():
    measurements = pd.read_parquet(os.path.join(TESTS_PATH, "data", "measurements.parquet.gz"))
    measurements_expected = pd.read_parquet(os.path.join(TESTS_PATH, "data", "measurements_hcn.parquet.gz"))
    samples = pd.read_parquet(os.path.join(TESTS_PATH, "data", "samples.parquet.gz"))
    features = pd.read_parquet(os.path.join(TESTS_PATH, "data", "features.parquet.gz"))

    measurements = hcn.normalize_by_hce(measurements, samples, features)

    measurements_joined = measurements_expected.set_index(
        ["PlateId", "PlatePosition", "ProbeId"]
    ).value.rename("value_expected").to_frame().join(
        measurements.set_index(
            ["PlateId", "PlatePosition", "ProbeId"]
        ).value.rename("value_test")
    )
    
    measurements_joined["value_diff_ppm"] = 1e6 * (
        measurements_joined.value_expected - measurements_joined.value_test
    ) / measurements_joined.value_expected

    assert measurements_joined.value_diff_ppm.max() < 1
