"""
Validation module for comparing IonTracks simulation results with experimental data.

This module provides tools for:
- Loading and validating experimental data
- Running IonTracks simulations with configurable parameters
- Comparing experimental and simulated results
- Generating plots and analysis reports
"""

from validation.comparison import ComparisonRunner
from validation.data_utils import load_experimental_data, validate_experimental_data

__all__ = ["ComparisonRunner", "load_experimental_data", "validate_experimental_data"]

