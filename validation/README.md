# Experimental Data Comparison Module

This module provides tools for comparing IonTracks simulation results with experimental measurements of ion recombination in ionization chambers.

## Overview

The validation module allows you to:
- Load experimental data from CSV files
- Run IonTracks simulations with configurable parameters (backend, grid size, etc.)
- Compare experimental and simulated results for both initial and general recombination
- Generate publication-quality plots and analysis reports

## Installation

The validation module is part of the IonTracks-Cython package. All required dependencies are included in the project's `requirements.txt`. Install them with:

```bash
pip install -r requirements.txt
```

This will install all necessary packages including pandas, numpy, matplotlib, seaborn, and pyyaml.

## Quick Start

### 1. Create a Configuration File

First, create a configuration template. It's recommended to place it in the same directory as your experimental data or in the `validation/` directory:

```bash
# Option 1: In validation directory (good for project-wide configs)
python -m validation.run_comparison --create-template validation/config.yaml

# Option 2: In experimental data directory (good for experiment-specific configs)
python -m validation.run_comparison --create-template experimental-data/2019_DCPT/config.yaml
```

This creates a template YAML file that you can edit to specify your experimental data path and simulation parameters.

### 2. Edit Configuration

Edit `config.yaml` to specify:

```yaml
experimental_data_path: "path/to/your/experimental_data.csv"
output_dir: "results"

simulation:
  backend: "cython"  # Options: cython, python, numba, cupy, parallel
  voltage_V: 200.0
  electrode_gap_cm: 0.2
  particle: "proton"
  RDD_model: "Gauss"  # Options: Gauss, Geiss
  grid_size_um: 5.0
  a0_nm: 8.0
  use_beta: False
  seed: null  # null for random seed

compare_initial_recombination: true
compare_continuous_beam: true
```

### 3. Prepare Experimental Data

Your experimental data CSV file should contain the following columns (exact names are flexible, see below):

**Required columns:**
- **Energy** (MeV): Proton or ion energy
  - Acceptable names: `Energy_MeV`, `energy_MeV`, `E_MeV`, `energy`
  
- **k_s**: Recombination correction factor
  - Acceptable names: `k_s`, `ks`, `recombination_factor`, `collection_efficiency`
  
- **Dose rate** (Gy/s): Dose rate in air or water
  - For air: `dose_rate_air_Gy_s`, `dose_rate_air`, `doserate_air_Gy_s`
  - For water: `dose_rate_water_Gy_s`, `dose_rate_water`, `doserate_water_Gy_s`
  - **Important**: Use air dose rate if your ionization chamber is filled with air (recommended)

**Optional columns:**
- Any other metadata columns will be preserved in output files

**Example CSV structure:**

```csv
Energy_MeV,dose_rate_air_Gy_s,k_s
150,3.665,1.0025
150,1.866,1.0013
226,5.61,1.0038
226,2.877,1.0019
```

**Note on dose rate units:**
- The code automatically converts Gy/s to Gy/min internally for calculations
- Always use the dose rate that matches your ionization chamber medium (air vs. water)
- Using the wrong medium (e.g., water dose rate for air-filled chamber) introduces ~13-14% error

### 4. Run Comparison

```bash
# Use the path to your config file
python -m validation.run_comparison validation/config.yaml
# or
python -m validation.run_comparison experimental-data/2019_DCPT/config.yaml
```

This will:
1. Load and validate your experimental data
2. Run IonTracks simulations for initial recombination (if enabled)
3. Run IonTracks simulations for continuous beam/general recombination (if enabled)
4. Compare results and calculate errors
5. Generate plots
6. Save results to CSV files

## Configuration Options

### Simulation Parameters

#### Backend Selection

Choose the computational backend:

- **`cython`** (default): Fast, compiled Cython code
- **`python`**: Pure Python (slower, but no compilation needed)
- **`numba`**: JIT-compiled NumPy code
- **`cupy`**: GPU-accelerated (requires CUDA-capable GPU)
- **`parallel`**: Parallel NumPy implementation

#### Physics Parameters

- **`voltage_V`**: Applied voltage in volts (typically 200-300 V)
- **`electrode_gap_cm`**: Electrode gap in cm (typically 0.1-0.2 cm)
- **`particle`**: Particle type (e.g., `"proton"`, `"carbon"`, `"helium"`)
- **`RDD_model`**: Radial dose distribution model
  - `"Gauss"`: Gaussian distribution (default)
  - `"Geiss"`: Geiss model
- **`grid_size_um`**: Spatial grid resolution in micrometers (smaller = more accurate but slower)
- **`a0_nm`**: Track core radius parameter in nanometers
- **`use_beta`**: Scale track core by β = v/c (usually False)

#### Computational Options

- **`seed`**: Random seed for reproducibility (null for random)
- **`SHOW_PLOT`**: Show simulation plots during calculation (False)
- **`PRINT_parameters`**: Print detailed parameters (False)
- **`debug`**: Enable debug mode (False)

### Comparison Options

- **`compare_initial_recombination`**: Compare initial recombination (fast, recommended)
- **`compare_continuous_beam`**: Compare general recombination (slow, may take minutes to hours)
- **`dose_rate_column`**: Which dose rate column to use (auto-detected if not specified)
- **`energy_column`**: Which energy column to use (auto-detected if not specified)
- **`ks_column`**: Which k_s column to use (auto-detected if not specified)

### Plotting Options

- **`plot_format`**: Output format (`"png"`, `"pdf"`, `"svg"`)
- **`plot_dpi`**: Resolution for raster formats (300 recommended)
- **`plot_style`**: Matplotlib style (`"whitegrid"`, `"darkgrid"`, etc.)

## Output Files

The comparison generates the following files in the output directory:

### CSV Files

1. **`comparison_initial.csv`**: Initial recombination comparison
   - Columns: `Energy_MeV`, `k_s_experimental`, `k_s_IonTracks`, `difference`, `relative_error_%`

2. **`comparison_continuous.csv`**: Full continuous beam comparison
   - Includes all original experimental columns plus IonTracks results and errors

3. **`comparison_continuous_clean.csv`**: Simplified continuous beam comparison
   - Only essential columns: energy, dose rate, k_s values, and errors

### Plot Files

1. **`initial_recombination_comparison.png`**: Initial recombination vs. energy
2. **`continuous_beam_comparison.png`**: Continuous beam results vs. dose rate (all energies)
3. **`relative_error.png`**: Relative error as function of dose rate

## Understanding Results

### Initial Recombination

Initial recombination occurs at very low dose rates where individual ion tracks don't overlap. The comparison:
- Extracts the minimum k_s value for each energy (lowest dose rate = initial recombination)
- Compares with IonTracks single-track calculations
- Shows how well the model predicts initial recombination

### General Recombination (Continuous Beam)

General recombination occurs at higher dose rates where track overlap becomes significant. The comparison:
- Runs IonTracks for each experimental condition (energy + dose rate)
- Compares simulated and experimental k_s values
- Calculates relative errors to assess model accuracy

### Error Metrics

- **Absolute error**: `k_s_IonTracks - k_s_experimental`
- **Relative error**: `100 × (k_s_IonTracks - k_s_experimental) / k_s_experimental`
- Statistics include mean, median, min, max, and standard deviation

## Example Workflow

### Example 1: Quick Initial Recombination Check

```yaml
experimental_data_path: "experimental-data/2019_DCPT/recombination_200V_data.csv"
output_dir: "results/initial_only"
simulation:
  backend: "cython"
  voltage_V: 200.0
  electrode_gap_cm: 0.2
compare_initial_recombination: true
compare_continuous_beam: false
```

### Example 2: Full Comparison with Custom Parameters

```yaml
experimental_data_path: "my_data.csv"
output_dir: "results/custom"
simulation:
  backend: "numba"
  voltage_V: 300.0
  electrode_gap_cm: 0.1
  particle: "proton"
  RDD_model: "Geiss"
  grid_size_um: 3.0
  seed: 42
compare_initial_recombination: true
compare_continuous_beam: true
```

### Example 3: High-Resolution Simulation

```yaml
simulation:
  backend: "cython"
  grid_size_um: 2.0  # Smaller = more accurate but slower
  a0_nm: 10.0
```

## Troubleshooting

### Common Issues

1. **"Could not find energy column"**
   - Check that your CSV has a column named one of: `Energy_MeV`, `energy_MeV`, `E_MeV`, `energy`
   - Or specify the exact column name in config: `energy_column: "your_column_name"`

2. **"Failed to calculate any results"**
   - Check that parameters are physically reasonable
   - Try a different backend (e.g., `python` instead of `cython`)
   - Enable debug mode: `simulation.debug: true`

3. **"Slow performance"**
   - Use `cython` or `numba` backend instead of `python`
   - Increase `grid_size_um` (less accurate but faster)
   - Disable `compare_continuous_beam` for quick initial checks

4. **"Import errors"**
   - Ensure IonTracks-Cython package is properly installed
   - Check that you're running from the correct directory
   - Verify all dependencies are installed

## Programmatic Usage

You can also use the validation module programmatically:

```python
from pathlib import Path
from validation.config import load_config
from validation.comparison import ComparisonRunner
from validation.plots import generate_all_plots

# Load configuration
config = load_config("config.yaml")

# Run comparison
runner = ComparisonRunner(config)
runner.run_all()
runner.save_results()

# Generate plots
generate_all_plots(
    runner.comparison_initial,
    runner.comparison_continuous,
    config,
)
```

## References

For more information about IonTracks and validation studies:

- Christensen, J.B. et al. (2020) "Mapping initial and general recombination in scanning proton pencil beams" *Phys. Med. Biol.* 65 115003
- Christensen, J.B., Tölli, H., Bassler, N. (2016) "A general algorithm for calculation of recombination losses in ionization chambers exposed to ion beams" *Medical Physics* 43.10: 5484-92

## License

Part of the IonTracks-Cython project.

