"""
Configuration management for experimental data comparison.

Supports loading configuration from YAML files with validation and defaults.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, Optional

import yaml


@dataclass
class SimulationConfig:
    """Configuration for IonTracks simulations."""

    # Backend selection
    backend: Literal["cython", "python", "numba", "cupy", "parallel"] = "cython"

    # Experimental setup parameters
    voltage_V: float = 200.0
    electrode_gap_cm: float = 0.2
    particle: str = "proton"

    # Simulation parameters
    RDD_model: Literal["Gauss", "Geiss"] = "Gauss"
    grid_size_um: float = 5.0
    a0_nm: float = 8.0
    use_beta: bool = False
    seed: Optional[int] = None

    # Optional simulation flags
    SHOW_PLOT: bool = False
    PRINT_parameters: bool = False
    debug: bool = False


@dataclass
class ComparisonConfig:
    """Configuration for comparison analysis."""

    # Paths
    experimental_data_path: Path
    output_dir: Path = field(default_factory=lambda: Path("results"))

    # Simulation configuration
    simulation: SimulationConfig = field(default_factory=SimulationConfig)

    # Comparison options
    compare_initial_recombination: bool = True
    compare_continuous_beam: bool = True

    # Data processing options (None for auto-detection)
    dose_rate_column: Optional[str] = None  # Auto-detect if None
    energy_column: Optional[str] = None  # Auto-detect if None
    ks_column: Optional[str] = None  # Auto-detect if None

    # Plotting options
    plot_format: str = "png"
    plot_dpi: int = 300
    plot_style: str = "whitegrid"

    def __post_init__(self):
        """Convert string paths to Path objects if needed."""
        if isinstance(self.experimental_data_path, str):
            self.experimental_data_path = Path(self.experimental_data_path)
        if isinstance(self.output_dir, str):
            self.output_dir = Path(self.output_dir)


def load_config(config_path: Path) -> ComparisonConfig:
    """
    Load configuration from YAML file.

    Parameters
    ----------
    config_path : Path
        Path to YAML configuration file

    Returns
    -------
    ComparisonConfig
        Loaded configuration object
    """
    config_path = Path(config_path)

    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with open(config_path, "r") as f:
        config_dict = yaml.safe_load(f)

    # Extract simulation config
    sim_dict = config_dict.get("simulation", {})
    simulation_config = SimulationConfig(**sim_dict)

    # Create comparison config
    config_dict["simulation"] = simulation_config
    config = ComparisonConfig(**config_dict)

    return config


def save_config_template(template_path: Path):
    """
    Save a template configuration file.

    Parameters
    ----------
    template_path : Path
        Path where to save the template
    """
    template = {
        "experimental_data_path": "path/to/experimental_data.csv",
        "output_dir": "results",
        "simulation": {
            "backend": "cython",  # Options: cython, python, numba, cupy, parallel
            "voltage_V": 200.0,
            "electrode_gap_cm": 0.2,
            "particle": "proton",
            "RDD_model": "Gauss",  # Options: Gauss, Geiss
            "grid_size_um": 5.0,
            "a0_nm": 8.0,
            "use_beta": False,
            "seed": None,  # None for random seed
            "SHOW_PLOT": False,
            "PRINT_parameters": False,
            "debug": False,
        },
        "compare_initial_recombination": True,
        "compare_continuous_beam": True,
        "dose_rate_column": None,  # None = auto-detect (will be null in YAML)
        "energy_column": None,  # None = auto-detect (will be null in YAML)
        "ks_column": None,  # None = auto-detect (will be null in YAML)
        "plot_format": "png",
        "plot_dpi": 300,
        "plot_style": "whitegrid",
    }

    with open(template_path, "w") as f:
        yaml.dump(template, f, default_flow_style=False, sort_keys=False)
