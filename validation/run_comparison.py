"""
Main entry point for running experimental data comparisons.

Usage:
    python -m validation.run_comparison config.yaml
"""

import argparse
import sys
from pathlib import Path

from validation.config import ComparisonConfig, load_config, save_config_template
from validation.comparison import ComparisonRunner
from validation.plots import generate_all_plots


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Compare IonTracks simulations with experimental data"
    )
    parser.add_argument(
        "config",
        type=str,
        nargs="?",
        help="Path to configuration YAML file (e.g., validation/config.yaml or experimental-data/2019_DCPT/config.yaml)",
    )
    parser.add_argument(
        "--create-template",
        type=str,
        metavar="PATH",
        help="Create a template configuration file at the specified path",
    )
    
    args = parser.parse_args()
    
    # Create template if requested
    if args.create_template:
        template_path = Path(args.create_template)
        save_config_template(template_path)
        print(f"✓ Created template configuration at: {template_path}")
        return
    
    # Load configuration
    if not args.config:
        parser.print_help()
        print("\nError: Configuration file is required (or use --create-template)")
        sys.exit(1)
    
    try:
        config = load_config(args.config)
    except Exception as e:
        print(f"Error loading configuration: {e}")
        sys.exit(1)
    
    # Run comparison
    print("=" * 70)
    print("IONTRACKS EXPERIMENTAL DATA COMPARISON")
    print("=" * 70)
    print(f"Experimental data: {config.experimental_data_path}")
    print(f"Output directory: {config.output_dir}")
    print(f"Backend: {config.simulation.backend}")
    print(f"Voltage: {config.simulation.voltage_V} V")
    print(f"Electrode gap: {config.simulation.electrode_gap_cm} cm")
    print(f"Particle: {config.simulation.particle}")
    
    try:
        runner = ComparisonRunner(config)
        runner.run_all()
        runner.save_results()
        generate_all_plots(
            runner.comparison_initial,
            runner.comparison_continuous,
            config,
        )
        
        print("\n" + "=" * 70)
        print("COMPARISON COMPLETED SUCCESSFULLY")
        print("=" * 70)
        
    except Exception as e:
        print(f"\nError during comparison: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

