"""
Main comparison logic for experimental data vs. IonTracks simulations.
"""

import sys
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from hadrons.functions import ks_initial_IonTracks, IonTracks_continuous_beam

from validation.config import ComparisonConfig, SimulationConfig
from validation.data_utils import load_experimental_data


class ComparisonRunner:
    """Runner for comparing experimental data with IonTracks simulations."""
    
    def __init__(self, config: ComparisonConfig):
        """
        Initialize comparison runner.
        
        Parameters
        ----------
        config : ComparisonConfig
            Configuration object
        """
        self.config = config
        self.config.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Load experimental data
        self.exp_data = load_experimental_data(
            config.experimental_data_path,
            energy_column=config.energy_column,
            ks_column=config.ks_column,
            dose_rate_column=config.dose_rate_column,
        )
        
        # Results storage
        self.initial_results: Optional[pd.DataFrame] = None
        self.continuous_results: Optional[pd.DataFrame] = None
        self.comparison_initial: Optional[pd.DataFrame] = None
        self.comparison_continuous: Optional[pd.DataFrame] = None
    
    def run_initial_recombination(self) -> pd.DataFrame:
        """
        Run initial recombination calculations and compare with experimental data.
        
        Returns
        -------
        pd.DataFrame
            Comparison results DataFrame
        """
        print("\n" + "=" * 70)
        print("INITIAL RECOMBINATION COMPARISON")
        print("=" * 70)
        
        sim_config = self.config.simulation
        energies_MeV = sorted(self.exp_data["Energy_MeV"].unique())
        
        initial_results_list = []
        
        for energy_MeV in energies_MeV:
            print(f"Calculating for {energy_MeV} MeV...")
            try:
                result = ks_initial_IonTracks(
                    E_MeV_u=energy_MeV,
                    voltage_V=sim_config.voltage_V,
                    electrode_gap_cm=sim_config.electrode_gap_cm,
                    particle=sim_config.particle,
                    RDD_model=sim_config.RDD_model,
                    grid_size_um=sim_config.grid_size_um,
                    a0_nm=sim_config.a0_nm,
                    use_beta=sim_config.use_beta,
                    debug=sim_config.debug,
                    SHOW_PLOT=sim_config.SHOW_PLOT,
                )
                initial_results_list.append(result)
            except Exception as e:
                print(f"  Error for {energy_MeV} MeV: {e}")
                continue
        
        if not initial_results_list:
            raise RuntimeError("Failed to calculate any results for Initial Recombination")
        
        self.initial_results = pd.concat(initial_results_list, ignore_index=True)
        
        # Compare with experimental data (lowest dose rate = initial recombination)
        comparison_list = []
        for energy_MeV in energies_MeV:
            exp_subset = self.exp_data[self.exp_data["Energy_MeV"] == energy_MeV]
            k_s_exp_min = exp_subset["k_s"].min()  # Lowest dose rate
            
            iontracks_subset = self.initial_results[
                self.initial_results["E_MeV_u"] == energy_MeV
            ]
            if len(iontracks_subset) > 0:
                k_s_iontracks = iontracks_subset["ks"].values[0]
                comparison_list.append(
                    {
                        "Energy_MeV": energy_MeV,
                        "k_s_experimental": k_s_exp_min,
                        "k_s_IonTracks": k_s_iontracks,
                        "difference": k_s_iontracks - k_s_exp_min,
                        "relative_error_%": 100
                        * (k_s_iontracks - k_s_exp_min)
                        / k_s_exp_min,
                    }
                )
        
        self.comparison_initial = pd.DataFrame(comparison_list)
        
        print("\nInitial Recombination Comparison:")
        print(self.comparison_initial.to_string(index=False))
        
        return self.comparison_initial
    
    def run_continuous_beam(self) -> pd.DataFrame:
        """
        Run continuous beam calculations and compare with experimental data.
        
        Returns
        -------
        pd.DataFrame
            Comparison results DataFrame
        """
        print("\n" + "=" * 70)
        print("CONTINUOUS BEAM COMPARISON (General Recombination)")
        print("=" * 70)
        print("WARNING: This may take several minutes...")
        
        sim_config = self.config.simulation
        continuous_results_list = []
        
        # Determine seed
        if sim_config.seed is None:
            import random
            seed = random.randint(1, int(1e7))
        else:
            seed = sim_config.seed
        
        total_rows = len(self.exp_data)
        for idx, row in self.exp_data.iterrows():
            if idx % max(1, total_rows // 10) == 0:
                progress = 100 * (idx + 1) / total_rows
                print(f"Progress: {idx+1}/{total_rows} ({progress:.1f}%)")
            
            try:
                result = IonTracks_continuous_beam(
                    E_MeV_u=row["Energy_MeV"],
                    voltage_V=sim_config.voltage_V,
                    doserate_Gy_min=row["dose_rate_Gy_min"],
                    electrode_gap_cm=sim_config.electrode_gap_cm,
                    particle=sim_config.particle,
                    grid_size_um=sim_config.grid_size_um,
                    backend=sim_config.backend,
                    PRINT_parameters=sim_config.PRINT_parameters,
                    SHOW_PLOT=sim_config.SHOW_PLOT,
                    myseed=seed + idx,  # Different seed for each calculation
                )
                continuous_results_list.append(result)
            except Exception as e:
                print(f"  Error for row {idx}: {e}")
                # Add NaN as result to preserve indices
                continuous_results_list.append(
                    pd.DataFrame([{"ks_IonTracks": np.nan, "E_MeV_u": row["Energy_MeV"]}])
                )
        
        if not continuous_results_list:
            raise RuntimeError("Failed to calculate any results for Continuous Beam")
        
        continuous_df = pd.concat(continuous_results_list, ignore_index=True)
        self.continuous_results = continuous_df
        
        # Create comparison DataFrame
        comparison_continuous = self.exp_data.copy()
        comparison_continuous["k_s_IonTracks"] = continuous_df["ks_IonTracks"].values
        comparison_continuous["difference"] = (
            comparison_continuous["k_s_IonTracks"] - comparison_continuous["k_s"]
        )
        comparison_continuous["relative_error_%"] = (
            100
            * comparison_continuous["difference"]
            / comparison_continuous["k_s"]
        )
        comparison_continuous["absolute_error"] = abs(
            comparison_continuous["difference"]
        )
        
        # Remove rows with NaN
        comparison_continuous = comparison_continuous.dropna(subset=["k_s_IonTracks"])
        self.comparison_continuous = comparison_continuous
        
        # Print summary
        print("\nContinuous Beam Comparison Summary:")
        print(f"Number of successful calculations: {len(comparison_continuous)}/{len(self.exp_data)}")
        if len(comparison_continuous) > 0:
            print(f"Mean absolute error: {comparison_continuous['absolute_error'].mean():.6f}")
            print(f"Mean relative error: {comparison_continuous['relative_error_%'].mean():.3f}%")
            print(f"Median relative error: {comparison_continuous['relative_error_%'].median():.3f}%")
            print(f"Max relative error: {comparison_continuous['relative_error_%'].max():.3f}%")
            print(f"Min relative error: {comparison_continuous['relative_error_%'].min():.3f}%")
            print(f"Standard deviation: {comparison_continuous['relative_error_%'].std():.3f}%")
        
        return self.comparison_continuous
    
    def run_all(self):
        """Run both initial recombination and continuous beam comparisons."""
        if self.config.compare_initial_recombination:
            self.run_initial_recombination()
        
        if self.config.compare_continuous_beam:
            self.run_continuous_beam()
    
    def save_results(self):
        """Save comparison results to CSV files."""
        print("\n" + "=" * 70)
        print("SAVING RESULTS")
        print("=" * 70)
        
        if self.comparison_initial is not None and len(self.comparison_initial) > 0:
            output_path = self.config.output_dir / "comparison_initial.csv"
            self.comparison_initial.to_csv(output_path, index=False)
            print(f"✓ Saved: {output_path}")
        
        if self.comparison_continuous is not None and len(self.comparison_continuous) > 0:
            # Save full comparison
            output_path = self.config.output_dir / "comparison_continuous.csv"
            self.comparison_continuous.to_csv(output_path, index=False)
            print(f"✓ Saved: {output_path}")
            
            # Save clean version
            clean_cols = [
                "Energy_MeV",
                "dose_rate_Gy_s",
                "k_s",
                "k_s_IonTracks",
                "difference",
                "relative_error_%",
                "absolute_error",
            ]
            available_cols = [col for col in clean_cols if col in self.comparison_continuous.columns]
            comparison_clean = self.comparison_continuous[available_cols]
            output_path_clean = self.config.output_dir / "comparison_continuous_clean.csv"
            comparison_clean.to_csv(output_path_clean, index=False)
            print(f"✓ Saved: {output_path_clean}")
        
        print(f"\nAll results saved in: {self.config.output_dir}")

