# Experimental data and how to compute results

## Basic information

The results compare `IonTracks-Cython` predictions against experimental recombination factors (`k_s`) for:

- proton beam
- 200 V
- 0.2 cm electrode gap (2 mm)
- `RDD_model = Gauss`
- backend `cython`

## How to regenerate results for re-benchmark

From the repository root:

1. Create a config file for this dataset (for example `validation/config_2019_dcpt_results.yaml`):

```yaml
experimental_data_path: experimental-data/2019_DCPT/recombination_200V_data.csv
output_dir: experimental-data/2019_DCPT/results
simulation:
  backend: cython
  voltage_V: 200.0
  electrode_gap_cm: 0.2
  particle: proton
  RDD_model: Gauss
  grid_size_um: 5.0
  a0_nm: 8.0
  use_beta: false
  seed: null
  SHOW_PLOT: false
  PRINT_parameters: false
  debug: false
compare_initial_recombination: true
compare_continuous_beam: true
dose_rate_column: dose_rate_air_Gy_s
energy_column: Energy_MeV
ks_column: k_s
plot_format: png
plot_dpi: 300
plot_style: whitegrid
```

2. Run:

```bash
python -m validation.run_comparison validation/config_2019_dcpt_results.yaml
```

This command regenerates:

- `comparison_initial.csv`
- `comparison_continuous.csv`
- `comparison_continuous_clean.csv`
- `initial_recombination_comparison.png`
- `continuous_beam_comparison.png`
- `relative_error.png`

## Notes

- Use air dose rate (`dose_rate_air_Gy_s`) for this dataset. The chamber is air-filled.