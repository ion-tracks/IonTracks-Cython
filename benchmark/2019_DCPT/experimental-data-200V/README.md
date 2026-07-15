# experimental-data
Contains ion recombination measurements for validations.

## Data Structure

### 2019_DCPT

Data acquired in 2019 at the Danish Center for Particle Therapy (DCPT) using:

- Advanced Markus chamber (parallel-plate), 2 mm electrode gap
- Proton energies: 70, 150, 226, 244 MeV
- Voltages: 50, 67, 83, 125, 200 V (chosen to look reasonable on a 1/V plot)
- Various dose rates (dependent on beam energy and degrader settings)

Publication: [IOP article](https://iopscience.iop.org/article/10.1088/1361-6560/ab8579/meta)

The recombination, calculated for 200 V, is stored in `2019_DCPT/recombination_200V_data.csv` with columns:

- `Energy_MeV`: proton kinetic energy in MeV
- `dose_Gy`: delivered dose in Gy
- `dose_rate_factor`: relative scaling factor for dose rate (not important)
- `time_s`: irradiation time (not important)
- `dose_rate_water_Gy_s`: dose rate in water in Gy/s
- `dose_rate_air_Gy_s`: dose rate in air in Gy/s
- `k_s`: recombination correction factor at 200 V
