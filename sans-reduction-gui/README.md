# SANS Reduction GUI (Standalone)

A browser-based GUI for reducing small-angle neutron scattering data collected at HFIR on the CG2 (GPSANS) and CG3 (BioSANS) instruments. The interface is built with the [Trame](https://kitware.github.io/trame/) framework using the MVVM pattern. Users configure sample and background runs, set reduction parameters, launch a local [drtsans](https://github.com/neutrons/drtsans) reduction, and inspect 1-D/2-D output files — all without connecting to the NDIP/Galaxy cluster.

## Requirements

- Network access to `analysis.sns.gov` (for ONCat experiment/sample lookup)
- The **sans** pixi environment installed at `/usr/local/pixi/sans/` (provides the drtsans Python used by the reduction worker)
- [Pixi](https://prefix.dev/) installed for the GUI environment

## How to run

```bash
cd sans-reduction-gui-standalone
pixi install          # first time only — resolves the GUI environment
pixi run gpsans       # launch the GPSANS interface
# or
pixi run biosans      # launch the BioSANS interface
```

## First-time ONCat authentication

On the first launch the app will open a browser window to authenticate with ONCat. After logging in, a token is cached at `~/.oncat_token.json`. Subsequent launches use the cached token automatically. If authentication fails, delete `~/.oncat_token.json` and relaunch.

## Two-environment setup

The app runs in two separate pixi environments:

| Environment | Location | Purpose |
|---|---|---|
| **sans-gui** (this repo) | `<repo>/.pixi/` | Trame web server, UI, ONCat |
| **sans** | `/usr/local/pixi/sans/` | drtsans reduction worker |

The GUI spawns the reduction worker using the `sans` environment's Python interpreter (`/usr/local/pixi/sans/.pixi/envs/default/bin/python`). Both environments must be present for reduction to work; the GUI itself will start without the `sans` environment, but clicking **Reduce** will fail.

## Developer notes

See [DEVELOPMENT.md](DEVELOPMENT.md) for contribution guidelines, linting, and testing instructions.
