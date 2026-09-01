import os
import warnings

import pandas as pd

from scripts import hybridization_control_normalization as hcn
from scripts import median_signal_normalization_calibrators as msncal
from scripts import plate_scale_normalization as psn

TESTS_PATH = os.path.dirname(os.path.abspath(__file__))

PPM_WARN_THRESHOLD = 1
PPM_FAIL_THRESHOLD = 10


def assert_matches_expected(measurements, measurements_expected):
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

    max_diff_ppm = measurements_joined.value_diff_ppm.max()
    if max_diff_ppm > PPM_WARN_THRESHOLD:
        warnings.warn(
            f"Max relative error {max_diff_ppm:.3f} ppm exceeds warning threshold of {PPM_WARN_THRESHOLD} ppm"
        )

    assert max_diff_ppm < PPM_FAIL_THRESHOLD


def test_calibrators_normalized_by_hce():
    measurements = pd.read_parquet(os.path.join(TESTS_PATH, "data", "measurements.parquet.gz"))
    measurements_expected = pd.read_parquet(os.path.join(TESTS_PATH, "data", "measurements_hcn.parquet.gz"))
    samples = pd.read_parquet(os.path.join(TESTS_PATH, "data", "samples.parquet.gz"))
    features = pd.read_parquet(os.path.join(TESTS_PATH, "data", "features.parquet.gz"))

    measurements = hcn.normalize_by_hce(measurements, samples, features)

    assert_matches_expected(measurements, measurements_expected)


def test_calibrators_normalized_by_msn():
    measurements = pd.read_parquet(os.path.join(TESTS_PATH, "data", "measurements_hcn.parquet.gz"))
    measurements_expected = pd.read_parquet(os.path.join(TESTS_PATH, "data", "measurements_msncal.parquet.gz"))
    samples = pd.read_parquet(os.path.join(TESTS_PATH, "data", "samples.parquet.gz"))
    features = pd.read_parquet(os.path.join(TESTS_PATH, "data", "features.parquet.gz"))

    measurements = msncal.normalize_by_msn_calibrators(measurements, samples, features)

    assert_matches_expected(measurements, measurements_expected)


def test_calibrators_normalized_by_plate_scale():
    measurements = pd.read_parquet(os.path.join(TESTS_PATH, "data", "measurements_msncal.parquet.gz"))
    measurements_expected = pd.read_parquet(os.path.join(TESTS_PATH, "data", "measurements_psn.parquet.gz"))
    samples = pd.read_parquet(os.path.join(TESTS_PATH, "data", "samples.parquet.gz"))
    features = pd.read_parquet(os.path.join(TESTS_PATH, "data", "features.parquet.gz"))

    measurements = psn.normalize_by_plate_scale(measurements, samples, features)

    assert_matches_expected(measurements, measurements_expected)
