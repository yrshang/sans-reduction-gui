"""Standalone drtsans reduction worker — runs inside the sans pixi environment.

Usage: reduction_worker.py <config_json_path> <instrument>
  instrument: "CG3" for BioSANS, "CG2" for GPSANS
"""

import json
import sys


def run_biosans(config: dict) -> None:
    from drtsans.mono.biosans import (
        load_all_files,
        plot_reduction_output,
        reduce_single_configuration,
        validate_reduction_parameters,
    )

    print("Validating BioSANS parameters...", flush=True)
    reduction_input = validate_reduction_parameters(config)
    print("Loading files...", flush=True)
    loaded = load_all_files(reduction_input)
    print("Running reduction...", flush=True)
    out = reduce_single_configuration(loaded, reduction_input)
    print("Plotting output...", flush=True)
    plot_reduction_output(out, reduction_input)


def run_gpsans(config: dict) -> None:
    from drtsans.mono.gpsans import reduction_parameters
    from drtsans.mono.gpsans.api import (
        load_all_files,
        plot_reduction_output,
        reduce_single_configuration,
    )

    print("Validating GPSANS parameters...", flush=True)
    cfg = reduction_parameters(config, permissible=False)
    print("Loading files...", flush=True)
    loaded = load_all_files(cfg)
    print("Running reduction...", flush=True)
    out = reduce_single_configuration(loaded, cfg)
    print("Plotting output...", flush=True)
    plot_reduction_output(out, cfg)


def main() -> None:
    if len(sys.argv) < 3:
        print(
            "Usage: reduction_worker.py <config_json_path> <instrument>",
            file=sys.stderr,
            flush=True,
        )
        sys.exit(1)

    config_path = sys.argv[1]
    instrument = sys.argv[2]

    with open(config_path) as f:
        config = json.load(f)

    try:
        if instrument in ("CG3", "BIOSANS"):
            run_biosans(config)
        elif instrument in ("CG2", "GPSANS"):
            run_gpsans(config)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr, flush=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
