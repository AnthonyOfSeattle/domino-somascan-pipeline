import os

import pandas as pd

from scripts import finalize_dataset as fd

TESTS_PATH = os.path.dirname(os.path.abspath(__file__))


def _load_fixtures():
    measurements = pd.read_parquet(os.path.join(TESTS_PATH, "data", "measurements_msnall.parquet.gz"))
    samples = pd.read_parquet(os.path.join(TESTS_PATH, "data", "samples.parquet.gz"))
    features = pd.read_parquet(os.path.join(TESTS_PATH, "data", "features.parquet.gz"))
    return measurements, samples, features


def test_finalize_dataset_subsamples_features_and_samples():
    measurements, samples, features = _load_fixtures()

    samples_final, features_final, measurements_final = fd.finalize_dataset(
        measurements, samples, features
    )

    assert (features_final.Type == fd.TYPE_PROTEIN).all()
    assert (features_final.Organism == fd.ORGANISM_HUMAN).all()
    assert (samples_final.SampleType == fd.SAMPLE_TYPE_SAMPLE).all()

    assert set(measurements_final.ProbeId) <= set(features_final.ProbeId)
    assert set(measurements_final.ProbeId) == set(features_final.ProbeId)

    measurements_wells = set(
        measurements_final[["PlateId", "PlatePosition"]].itertuples(index=False, name=None)
    )
    samples_wells = set(
        samples_final[["PlateId", "PlatePosition"]].itertuples(index=False, name=None)
    )
    assert measurements_wells == samples_wells


def test_finalize_dataset_excludes_non_human_and_non_sample():
    measurements, samples, features = _load_fixtures()

    samples_final, features_final, measurements_final = fd.finalize_dataset(
        measurements, samples, features
    )

    assert len(features_final) < len(features)
    assert len(samples_final) < len(samples)
    assert len(measurements_final) < len(measurements)
