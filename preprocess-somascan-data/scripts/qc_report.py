import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

from pathlib import Path
from sklearn import decomposition

TYPE_PROTEIN = "Protein"
SAMPLE_TYPE_SAMPLE = "Sample"
SAMPLE_TYPE_CALIBRATOR = "Calibrator"


def plot_sample_pca(
    measurements: pd.DataFrame,
    samples: pd.DataFrame,
    features: pd.DataFrame,
    title: str = "Sample PCA"
) -> plt.Figure:

    # 1. Restrict to sample wells and protein probes, and pivot to one row per well
    measurements_wide = measurements.merge(
        samples.loc[samples.SampleType == SAMPLE_TYPE_SAMPLE, ["PlateId", "PlatePosition"]],
        how="inner"
    ).merge(
        features.loc[features.Type == TYPE_PROTEIN, "ProbeId"],
        how="inner"
    ).pivot(
        index=["PlateId", "PlatePosition"],
        columns="ProbeId",
        values="value"
    )

    # 2. Run PCA
    pca = decomposition.PCA(n_components=2)
    x = pca.fit_transform(measurements_wide)

    # 3. Plot the first two components, colored by plate
    fig, ax = plt.subplots(figsize=[6.25, 6])
    sns.scatterplot(
        x=x[:, 0],
        y=x[:, 1],
        hue=measurements_wide.reset_index().PlateId,
        s=50,
        linewidth=0,
        alpha=.75,
        ax=ax
    )
    ax.legend(title="Plate ID", ncol=2, bbox_to_anchor=(1, 1))
    ax.set_xlabel(f"PC1 ({pca.explained_variance_ratio_[0] * 100:.1f}%)")
    ax.set_ylabel(f"PC2 ({pca.explained_variance_ratio_[1] * 100:.1f}%)")
    ax.set_title(title)
    fig.tight_layout()

    return fig


def plot_calibrator_cv(
    measurements: pd.DataFrame,
    samples: pd.DataFrame,
    features: pd.DataFrame,
    title: str = "Calibrator CV"
) -> plt.Figure:

    # 1. Restrict to calibrator wells
    measurements_calibrators = samples.loc[
        samples.SampleType == SAMPLE_TYPE_CALIBRATOR,
        ["PlateId", "PlatePosition"]
    ].merge(measurements)

    # 2. Calculate per-plate/probe CV (%)
    std = measurements_calibrators.groupby(["PlateId", "ProbeId"]).value.std()
    mean = measurements_calibrators.groupby(["PlateId", "ProbeId"]).value.mean()
    cv = (100 * std / mean).rename("value").to_frame().reset_index()

    # 3. Plot the CV distribution per plate
    fig, ax = plt.subplots(figsize=[7, 5])
    sns.kdeplot(data=cv[cv.value < 100], x="value", hue="PlateId", ax=ax)
    ax.set_xlabel("CV (%)")
    handles = ax.get_legend().legend_handles
    labels = [t.get_text() for t in ax.get_legend().get_texts()]
    ax.legend(handles, labels, title="Plate ID", ncol=2, bbox_to_anchor=(1, 1))
    ax.set_title(title)
    fig.tight_layout()

    return fig


if __name__ == "__main__":
    # 1. Read input
    stage = Path("/workflow/inputs/stage").read_text().strip()
    measurements = pd.read_csv("/workflow/inputs/measurements")
    samples = pd.read_csv("/workflow/inputs/samples")
    features = pd.read_csv("/workflow/inputs/features")

    # 2. Generate QC plots
    fig_pca = plot_sample_pca(measurements, samples, features, title=f"Sample PCA ({stage})")
    fig_cv = plot_calibrator_cv(measurements, samples, features, title=f"Calibrator CV ({stage})")

    # 3. Write workflow outputs
    fig_pca.savefig(f"/workflow/outputs/pca_{stage}.png", dpi=150)
    fig_cv.savefig(f"/workflow/outputs/cv_{stage}.png", dpi=150)
