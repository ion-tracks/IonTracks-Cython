"""
Plotting functions for comparison results.
"""

from pathlib import Path
from typing import Optional

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from validation.config import ComparisonConfig


def plot_initial_recombination(
    comparison_df: pd.DataFrame,
    output_path: Path,
    config: ComparisonConfig,
):
    """
    Plot initial recombination comparison.
    
    Parameters
    ----------
    comparison_df : pd.DataFrame
        Comparison DataFrame with initial recombination results
    output_path : Path
        Path to save the plot
    config : ComparisonConfig
        Configuration object
    """
    if len(comparison_df) == 0:
        print("Warning: No data to plot for initial recombination")
        return
    
    sns.set_style(config.plot_style)
    plt.rcParams["figure.dpi"] = config.plot_dpi
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    ax.plot(
        comparison_df["Energy_MeV"],
        comparison_df["k_s_experimental"],
        "o-",
        label="Experimental",
        markersize=10,
        linewidth=2,
        color="blue",
    )
    ax.plot(
        comparison_df["Energy_MeV"],
        comparison_df["k_s_IonTracks"],
        "s--",
        label="IonTracks",
        markersize=10,
        linewidth=2,
        color="red",
    )
    
    ax.set_xlabel("Proton Energy [MeV]", fontsize=12)
    ax.set_ylabel("$k_s$", fontsize=12)
    ax.set_title("Initial Recombination: Experiment vs. IonTracks", fontsize=14)
    ax.legend(fontsize=11)
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(output_path, format=config.plot_format, dpi=config.plot_dpi)
    plt.close()
    print(f"✓ Saved: {output_path.name}")


def plot_continuous_beam(
    comparison_df: pd.DataFrame,
    output_path: Path,
    config: ComparisonConfig,
):
    """
    Plot continuous beam comparison.
    
    Parameters
    ----------
    comparison_df : pd.DataFrame
        Comparison DataFrame with continuous beam results
    output_path : Path
        Path to save the plot
    config : ComparisonConfig
        Configuration object
    """
    if len(comparison_df) == 0:
        print("Warning: No data to plot for continuous beam")
        return
    
    sns.set_style(config.plot_style)
    plt.rcParams["figure.dpi"] = config.plot_dpi
    
    fig, ax = plt.subplots(figsize=(12, 7))
    
    energies_MeV = sorted(comparison_df["Energy_MeV"].unique())
    colors = plt.cm.tab10(np.linspace(0, 1, len(energies_MeV)))
    
    for i, energy in enumerate(energies_MeV):
        subset = comparison_df[comparison_df["Energy_MeV"] == energy]
        subset = subset.sort_values("dose_rate_Gy_s")
        
        if len(subset) > 0:
            ax.plot(
                subset["dose_rate_Gy_s"],
                subset["k_s"],
                "o-",
                label=f"Exp. {energy} MeV",
                markersize=6,
                linewidth=1.5,
                color=colors[i],
                alpha=0.7,
            )
            ax.plot(
                subset["dose_rate_Gy_s"],
                subset["k_s_IonTracks"],
                "s--",
                label=f"IonTracks {energy} MeV",
                markersize=6,
                linewidth=1.5,
                color=colors[i],
            )
    
    ax.set_xlabel("Dose Rate in Air [Gy/s]", fontsize=12)
    ax.set_ylabel("$k_s$", fontsize=12)
    ax.set_title("Continuous Beam: Experiment vs. IonTracks", fontsize=14)
    ax.legend(ncol=2, fontsize=9)
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(output_path, format=config.plot_format, dpi=config.plot_dpi)
    plt.close()
    print(f"✓ Saved: {output_path.name}")


def plot_relative_error(
    comparison_df: pd.DataFrame,
    output_path: Path,
    config: ComparisonConfig,
):
    """
    Plot relative error as a function of dose rate.
    
    Parameters
    ----------
    comparison_df : pd.DataFrame
        Comparison DataFrame with continuous beam results
    output_path : Path
        Path to save the plot
    config : ComparisonConfig
        Configuration object
    """
    if len(comparison_df) == 0:
        print("Warning: No data to plot for relative error")
        return
    
    sns.set_style(config.plot_style)
    plt.rcParams["figure.dpi"] = config.plot_dpi
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    energies_MeV = sorted(comparison_df["Energy_MeV"].unique())
    colors = plt.cm.tab10(np.linspace(0, 1, len(energies_MeV)))
    
    for i, energy in enumerate(energies_MeV):
        subset = comparison_df[comparison_df["Energy_MeV"] == energy]
        subset = subset.sort_values("dose_rate_Gy_s")
        
        if len(subset) > 0:
            ax.plot(
                subset["dose_rate_Gy_s"],
                subset["relative_error_%"],
                "o-",
                label=f"{energy} MeV",
                markersize=6,
                linewidth=1.5,
                color=colors[i],
            )
    
    ax.axhline(y=0, color="r", linestyle=":", linewidth=2)
    ax.set_xlabel("Dose Rate in Air [Gy/s]", fontsize=12)
    ax.set_ylabel("Relative Error [%]", fontsize=12)
    ax.set_title("IonTracks Relative Error", fontsize=14)
    ax.legend(fontsize=11)
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(output_path, format=config.plot_format, dpi=config.plot_dpi)
    plt.close()
    print(f"✓ Saved: {output_path.name}")


def generate_all_plots(
    comparison_initial: Optional[pd.DataFrame],
    comparison_continuous: Optional[pd.DataFrame],
    config: ComparisonConfig,
):
    """
    Generate all comparison plots.
    
    Parameters
    ----------
    comparison_initial : Optional[pd.DataFrame]
        Initial recombination comparison DataFrame
    comparison_continuous : Optional[pd.DataFrame]
        Continuous beam comparison DataFrame
    config : ComparisonConfig
        Configuration object
    """
    print("\n" + "=" * 70)
    print("GENERATING PLOTS")
    print("=" * 70)
    
    if comparison_initial is not None and len(comparison_initial) > 0:
        plot_initial_recombination(
            comparison_initial,
            config.output_dir / "initial_recombination_comparison.png",
            config,
        )
    
    if comparison_continuous is not None and len(comparison_continuous) > 0:
        plot_continuous_beam(
            comparison_continuous,
            config.output_dir / "continuous_beam_comparison.png",
            config,
        )
        
        plot_relative_error(
            comparison_continuous,
            config.output_dir / "relative_error.png",
            config,
        )

