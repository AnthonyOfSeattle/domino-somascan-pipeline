import os

import matplotlib.pyplot as plt
import pandas as pd

from scripts import qc_report

TESTS_PATH = os.path.dirname(os.path.abspath(__file__))


def _load_fixtures():
    measurements = pd.read_parquet(os.path.join(TESTS_PATH, "data", "measurements.parquet.gz"))
    samples = pd.read_parquet(os.path.join(TESTS_PATH, "data", "samples.parquet.gz"))
    features = pd.read_parquet(os.path.join(TESTS_PATH, "data", "features.parquet.gz"))
    return measurements, samples, features


def test_plot_sample_pca():
    measurements, samples, features = _load_fixtures()

    fig = qc_report.plot_sample_pca(measurements, samples, features)

    assert isinstance(fig, plt.Figure)
    ax = fig.axes[0]
    assert ax.get_xlabel().startswith("PC1")
    assert ax.get_ylabel().startswith("PC2")
    plt.close(fig)


def test_plot_calibrator_cv():
    measurements, samples, features = _load_fixtures()

    fig = qc_report.plot_calibrator_cv(measurements, samples, features)

    assert isinstance(fig, plt.Figure)
    assert fig.axes[0].get_xlabel() == "CV (%)"
    plt.close(fig)
