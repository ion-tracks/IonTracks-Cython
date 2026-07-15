"""
Comprehensive script for testing experimental data from DCPT 2019

This script compares IonTracks calculation results with actual measurements
performed at Danish Center for Particle Therapy in 2019.

Usage:
    python test_experimental_data.py
"""

import argparse
import io
import sys
from pathlib import Path

# Ustaw kodowanie UTF-8 dla stdout/stderr (ważne na Windows)
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

# Add path to main project directory in a robust way
def find_project_root(start_path: Path, marker: str = "hadrons"):
    current = start_path.resolve()
    while current != current.parent:
        if (current / marker).is_dir():
            return current
        current = current.parent
    raise RuntimeError(f"Could not find project root containing '{marker}' directory.")
project_root = find_project_root(Path(__file__).parent)
sys.path.insert(0, str(project_root))

from hadrons.functions import (  # noqa: E402
    E_MeV_u_to_LET_keV_um,
    IonTracks_continuous_beam,
    ks_initial_IonTracks,
)

# ============================================================================
# CONFIGURATION
# ============================================================================

# Parse command line arguments
parser = argparse.ArgumentParser(description="Test experimental data from DCPT 2019")
parser.add_argument(
    "--backend",
    type=str,
    default="cython",
    choices=["cython", "numba", "python"],
    help="Backend to use: cython, numba, or python",
)
parser.add_argument(
    "--output-dir",
    type=str,
    default=None,
    help="Output directory (default: results in script directory)",
)
args = parser.parse_args()

DATA_PATH = Path(__file__).parent / "recombination_200V_data.csv"
if args.output_dir:
    OUTPUT_DIR = Path(args.output_dir)
else:
    OUTPUT_DIR = Path(__file__).parent / "results"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Experimental parameters
VOLTAGE_V = 200
ELECTRODE_GAP_CM = 0.2  # 2 mm
PARTICLE = "proton"
RDD_MODEL = "Gauss"  # or "Geiss"
GRID_SIZE_UM = 5.0
BACKEND = args.backend

# ============================================================================
# LOAD DATA
# ============================================================================

print("=" * 70)
print("TESTING EXPERIMENTAL DATA DCPT 2019")
print("=" * 70)

if not DATA_PATH.exists():
    print(f"ERROR: File not found {DATA_PATH}")
    print("Make sure recombination_200V_data.csv exists.")
    sys.exit(1)

exp_data = pd.read_csv(DATA_PATH)
# IMPORTANT: Use dose_rate_air_Gy_s (not dose_rate_water_Gy_s) because:
# - Ionization chamber is filled with AIR
# - doserate_to_fluence() converts dose rate in AIR to fluence
# - LET is calculated for AIR
# - Using water dose rate would cause ~13-14% error!
exp_data["dose_rate_air_Gy_min"] = exp_data["dose_rate_air_Gy_s"] * 60

print(f"\nLoaded {len(exp_data)} experimental measurements")
print(f"Energies: {sorted(exp_data['Energy_MeV'].unique())} MeV")
print(f"Voltage: {VOLTAGE_V} V")
print(f"Electrode gap: {ELECTRODE_GAP_CM} cm")

# ============================================================================
# METHOD 1: INITIAL RECOMBINATION (single tracks)
# ============================================================================

print("\n" + "=" * 70)
print("METHOD 1: INITIAL RECOMBINATION")
print("=" * 70)

energies_MeV = sorted(exp_data["Energy_MeV"].unique())
initial_results = []

for energy_MeV in energies_MeV:
    print(f"Calculating for {energy_MeV} MeV...")
    try:
        result = ks_initial_IonTracks(
            E_MeV_u=energy_MeV,
            voltage_V=VOLTAGE_V,
            electrode_gap_cm=ELECTRODE_GAP_CM,
            particle=PARTICLE,
            RDD_model=RDD_MODEL,
            grid_size_um=GRID_SIZE_UM,
        )
        initial_results.append(result)
    except Exception as e:
        print(f"  Error for {energy_MeV} MeV: {e}")
        continue

if not initial_results:
    print("ERROR: Failed to calculate any results for Initial Recombination")
    sys.exit(1)

initial_df = pd.concat(initial_results, ignore_index=True)

# Number of ions is now calculated by numerical integration in the solver
# No need for analytical calculations - values are already in initial_df

# Compare with experimental data (lowest dose rate = initial recombination)
comparison_initial = []
for energy_MeV in energies_MeV:
    exp_subset = exp_data[exp_data["Energy_MeV"] == energy_MeV]
    k_s_exp_min = exp_subset["k_s"].min()  # Lowest dose rate

    iontracks_subset = initial_df[initial_df["E_MeV_u"] == energy_MeV]
    if len(iontracks_subset) > 0:
        k_s_iontracks = iontracks_subset["ks"].values[0]
        n_positive = iontracks_subset["n_positive_ions"].values[0]
        n_negative = iontracks_subset["n_negative_ions"].values[0]
        comparison_initial.append(
            {
                "Energy_MeV": energy_MeV,
                "k_s_experimental": k_s_exp_min,
                "k_s_IonTracks": k_s_iontracks,
                "difference": k_s_iontracks - k_s_exp_min,
                "relative_error_%": 100 * (k_s_iontracks - k_s_exp_min) / k_s_exp_min,
                "n_positive_ions": n_positive,
                "n_negative_ions": n_negative,
            }
        )

comparison_initial_df = pd.DataFrame(comparison_initial)
print("\nInitial Recombination Comparison:")
# Format for display
display_initial = comparison_initial_df.copy()
display_initial["n_positive_ions"] = display_initial["n_positive_ions"].apply(
    lambda x: f"{x:.2e}"
)
display_initial["n_negative_ions"] = display_initial["n_negative_ions"].apply(
    lambda x: f"{x:.2e}"
)
print(display_initial.to_string(index=False))

# ============================================================================
# METHOD 2: CONTINUOUS BEAM (general recombination)
# ============================================================================

print("\n" + "=" * 70)
print("METHOD 2: CONTINUOUS BEAM (General Recombination)")
print("=" * 70)
print("WARNING: This may take several minutes...")

continuous_results = []

for idx, row in exp_data.iterrows():
    if idx % 5 == 0:
        print(
            f"Progress: {idx + 1}/{len(exp_data)} ({100 * (idx + 1) / len(exp_data):.1f}%)"
        )

    try:
        result = IonTracks_continuous_beam(
            E_MeV_u=row["Energy_MeV"],
            voltage_V=VOLTAGE_V,
            doserate_Gy_min=row["dose_rate_air_Gy_min"],
            electrode_gap_cm=ELECTRODE_GAP_CM,
            particle=PARTICLE,
            grid_size_um=GRID_SIZE_UM,
            backend=BACKEND,
        )
        continuous_results.append(result)
    except Exception as e:
        print(f"  Error for row {idx}: {e}")
        # Add NaN as result to preserve indices
        continuous_results.append(
            pd.DataFrame(
                [
                    {
                        "ks_IonTracks": np.nan,
                        "E_MeV_u": row["Energy_MeV"],
                        "LET_keV_um": np.nan,
                        "fluencerate_cm2_s": np.nan,
                        "doserate_Gy_min": row["dose_rate_air_Gy_min"],
                    }
                ]
            )
        )

if not continuous_results:
    print("ERROR: Failed to calculate any results for Continuous Beam")
    sys.exit(1)

continuous_df = pd.concat(continuous_results, ignore_index=True)

# Number of ions is now calculated by numerical integration in the solver
# For continuous beam, we need to calculate ions per second from total ions
# The solver returns total ions at the end of simulation, so we need to estimate rate

# Get simulation time from solver parameters (approximate)
# Simulation time ≈ separation_time_steps * dt
# separation_time_steps ≈ electrode_gap / (2 * mobility * E * dt)
# For display purposes, we'll use the total ions and estimate per-second rate
ion_mobility = 1.65  # cm^2/(V·s)
Efield_V_cm = VOLTAGE_V / ELECTRODE_GAP_CM
# Approximate dt (will vary, but this is for display only)
approx_dt = 1e-9  # seconds (typical value)
separation_time_steps = int(ELECTRODE_GAP_CM / (2. * ion_mobility * Efield_V_cm * approx_dt))
n_separation_times = 3
simulation_time_s = separation_time_steps * n_separation_times * approx_dt

for idx, row in continuous_df.iterrows():
    # Skip if ks_IonTracks is NaN (calculation failed)
    if pd.isna(row.get("ks_IonTracks", np.nan)):
        continuous_df.loc[idx, "n_positive_ions_per_s"] = np.nan
        continuous_df.loc[idx, "n_negative_ions_per_s"] = np.nan
        continuous_df.loc[idx, "n_positive_ions"] = np.nan
        continuous_df.loc[idx, "n_negative_ions"] = np.nan
        continue
    
    # Get total ions from solver (already calculated by numerical integration)
    n_positive_total = row.get("n_positive_ions", 0.0)
    n_negative_total = row.get("n_negative_ions", 0.0)
    
    # Calculate ions per second (average rate over simulation time)
    if simulation_time_s > 0:
        ions_per_second_positive = n_positive_total / simulation_time_s
        ions_per_second_negative = n_negative_total / simulation_time_s
    else:
        ions_per_second_positive = 0.0
        ions_per_second_negative = 0.0
    
    continuous_df.loc[idx, "n_positive_ions_per_s"] = ions_per_second_positive
    continuous_df.loc[idx, "n_negative_ions_per_s"] = ions_per_second_negative
    continuous_df.loc[idx, "n_positive_ions"] = n_positive_total
    continuous_df.loc[idx, "n_negative_ions"] = n_negative_total

# Comparison
# NOTE: We use dose_rate_air_Gy_s for calculations (not dose_rate_water_Gy_s)
# because the ionization chamber is filled with air, not water.
comparison_continuous = exp_data.copy()
comparison_continuous["k_s_IonTracks"] = continuous_df["ks_IonTracks"].values
comparison_continuous["n_positive_ions_per_s"] = continuous_df["n_positive_ions_per_s"].values
comparison_continuous["n_negative_ions_per_s"] = continuous_df["n_negative_ions_per_s"].values
comparison_continuous["n_positive_ions"] = continuous_df["n_positive_ions"].values
comparison_continuous["n_negative_ions"] = continuous_df["n_negative_ions"].values
comparison_continuous["difference"] = (
    comparison_continuous["k_s_IonTracks"] - comparison_continuous["k_s"]
)
comparison_continuous["relative_error_%"] = (
    100 * comparison_continuous["difference"] / comparison_continuous["k_s"]
)
comparison_continuous["absolute_error"] = abs(comparison_continuous["difference"])

# Remove rows with NaN
comparison_continuous = comparison_continuous.dropna(subset=["k_s_IonTracks"])

# Print comparison table
print("\nContinuous Beam Comparison:")
# Create a display-friendly version for printing
display_continuous = comparison_continuous[
    [
        "Energy_MeV",
        "dose_rate_air_Gy_s",
        "k_s",
        "k_s_IonTracks",
        "difference",
        "relative_error_%",
        "n_positive_ions_per_s",
        "n_negative_ions_per_s",
    ]
].copy()
display_continuous = display_continuous.sort_values(
    ["Energy_MeV", "dose_rate_air_Gy_s"]
)
# Format for better readability
display_continuous["dose_rate_air_Gy_s"] = display_continuous[
    "dose_rate_air_Gy_s"
].round(3)
display_continuous["k_s"] = display_continuous["k_s"].round(6)
display_continuous["k_s_IonTracks"] = display_continuous["k_s_IonTracks"].round(6)
display_continuous["difference"] = display_continuous["difference"].round(6)
display_continuous["relative_error_%"] = display_continuous["relative_error_%"].round(3)
display_continuous["n_positive_ions_per_s"] = display_continuous[
    "n_positive_ions_per_s"
].apply(lambda x: f"{x:.2e}")
display_continuous["n_negative_ions_per_s"] = display_continuous[
    "n_negative_ions_per_s"
].apply(lambda x: f"{x:.2e}")
print(display_continuous.to_string(index=False))

print("\n=== Error Statistics ===")
print(
    f"Number of successful calculations: {len(comparison_continuous)}/{len(exp_data)}"
)
if len(comparison_continuous) > 0:
    print(f"Mean absolute error: {comparison_continuous['absolute_error'].mean():.6f}")
    print(
        f"Mean relative error: {comparison_continuous['relative_error_%'].mean():.3f}%"
    )
    print(
        f"Median relative error: {comparison_continuous['relative_error_%'].median():.3f}%"
    )
    print(f"Max relative error: {comparison_continuous['relative_error_%'].max():.3f}%")
    print(f"Min relative error: {comparison_continuous['relative_error_%'].min():.3f}%")
    print(f"Standard deviation: {comparison_continuous['relative_error_%'].std():.3f}%")

print("\n=== Ion Statistics ===")
if len(comparison_continuous) > 0:
    print(f"Mean positive ions per second: {comparison_continuous['n_positive_ions_per_s'].mean():.2e}")
    print(f"Mean negative ions per second: {comparison_continuous['n_negative_ions_per_s'].mean():.2e}")
    print(f"Min positive ions per second: {comparison_continuous['n_positive_ions_per_s'].min():.2e}")
    print(f"Max positive ions per second: {comparison_continuous['n_positive_ions_per_s'].max():.2e}")

# ============================================================================
# VISUALIZATION
# ============================================================================

print("\n" + "=" * 70)
print("GENERATING PLOTS")
print("=" * 70)

# Set plot style
sns.set_style("whitegrid")
plt.rcParams["figure.dpi"] = 100

# Plot 1: Initial Recombination
if len(comparison_initial_df) > 0:
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(
        comparison_initial_df["Energy_MeV"],
        comparison_initial_df["k_s_experimental"],
        "o-",
        label="Experimental",
        markersize=10,
        linewidth=2,
        color="blue",
    )
    ax.plot(
        comparison_initial_df["Energy_MeV"],
        comparison_initial_df["k_s_IonTracks"],
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
    plt.savefig(OUTPUT_DIR / "initial_recombination_comparison.png", dpi=300)
    print("[OK] Saved: initial_recombination_comparison.png")

# Plot 2: Continuous Beam - all energies
if len(comparison_continuous) > 0:
    fig, ax = plt.subplots(figsize=(12, 7))
    colors = plt.cm.tab10(np.linspace(0, 1, len(energies_MeV)))

    for i, energy in enumerate(energies_MeV):
        subset_exp = comparison_continuous[
            comparison_continuous["Energy_MeV"] == energy
        ]
        subset_exp = subset_exp.sort_values("dose_rate_air_Gy_s")

        subset_iontracks = continuous_df[continuous_df["E_MeV_u"] == energy]
        if len(subset_iontracks) > 0:
            subset_iontracks = subset_iontracks.sort_values("doserate_Gy_min")

            ax.plot(
                subset_exp["dose_rate_air_Gy_s"],
                subset_exp["k_s"],
                "o-",
                label=f"Exp. {energy} MeV",
                markersize=6,
                linewidth=1.5,
                color=colors[i],
                alpha=0.7,
            )
            ax.plot(
                subset_iontracks["doserate_Gy_min"] / 60,
                subset_iontracks["ks_IonTracks"],
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
    plt.savefig(OUTPUT_DIR / "continuous_beam_comparison.png", dpi=300)
    print("[OK] Saved: continuous_beam_comparison.png")

    # Plot 3: Relative error
    fig, ax = plt.subplots(figsize=(10, 6))
    for i, energy in enumerate(energies_MeV):
        subset = comparison_continuous[comparison_continuous["Energy_MeV"] == energy]
        subset = subset.sort_values("dose_rate_air_Gy_s")
        if len(subset) > 0:
            ax.plot(
                subset["dose_rate_air_Gy_s"],
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
    plt.savefig(OUTPUT_DIR / "relative_error.png", dpi=300)
    print("[OK] Saved: relative_error.png")

# ============================================================================
# SAVE RESULTS
# ============================================================================

print("\n" + "=" * 70)
print("SAVING RESULTS")
print("=" * 70)

# Save comparisons to CSV
if len(comparison_initial_df) > 0:
    comparison_initial_df.to_csv(OUTPUT_DIR / "comparison_initial.csv", index=False)
    print("[OK] Saved: comparison_initial.csv")
    print(f"  Includes ion counts: positive and negative ions per track")

if len(comparison_continuous) > 0:
    # Save full comparison (includes all original columns for reference)
    comparison_continuous.to_csv(OUTPUT_DIR / "comparison_continuous.csv", index=False)
    print("[OK] Saved: comparison_continuous.csv")
    print("  NOTE: Calculations used dose_rate_air_Gy_s (not dose_rate_water_Gy_s)")

    # Also save a clean version with only essential columns
    comparison_clean = comparison_continuous[
        [
            "Energy_MeV",
            "dose_rate_air_Gy_s",
            "k_s",
            "k_s_IonTracks",
            "difference",
            "relative_error_%",
            "absolute_error",
        ]
    ]
    comparison_clean = comparison_continuous[
        [
            "Energy_MeV",
            "dose_rate_air_Gy_s",
            "k_s",
            "k_s_IonTracks",
            "difference",
            "relative_error_%",
            "absolute_error",
            "n_positive_ions_per_s",
            "n_negative_ions_per_s",
        ]
    ]
    comparison_clean.to_csv(OUTPUT_DIR / "comparison_continuous_clean.csv", index=False)
    print("[OK] Saved: comparison_continuous_clean.csv (essential columns only)")
    print(f"  Includes ion counts: positive and negative ions per second")

print(f"\nAll results saved in: {OUTPUT_DIR}")
print("\n" + "=" * 70)
print("TESTING COMPLETED")
print("=" * 70)
