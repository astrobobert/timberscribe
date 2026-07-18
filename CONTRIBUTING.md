# Contributing to TimberScribe

TimberScribe is a Flask server that drives a laser print head over WiFi (the
sled's GRBL controller hosts its own hotspot) — but **you don't need the
hardware to contribute.** The hardware layer falls back to a simulation mode
whenever the controller is unreachable (no sled hotspot, no serial port), so
the full web UI and job pipeline run on any machine with Python 3.

## Dev setup (any OS)

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
flask --app run:app run --debug --host 0.0.0.0 --port 5000
```

Open `http://localhost:5000`, upload a `.tsj` file, and exercise the job list
/ face selector / print flow in simulation. Sample `.tsj` files come from
TimberDraw's scribe export, or hand-write one from the spec below.

On the real rig: `python run.py` on a laptop joined to the sled's hotspot —
see the [README](README.md).

## Ground rules

- **[TSJ_SPEC.md](TSJ_SPEC.md) is the contract.** `app/tsj_parser.py` is its
  reference validator. Any schema change must land in the spec, this parser,
  and the writer in the [timberdraw](https://github.com/astrobobert/timberdraw)
  repo (`Managed/ScribeTsj.cs`) together — and stay additive within v2.x
  (consumers skip unknown entity types).
- **Simulation must keep working.** Don't let a change require a reachable
  controller (or a real serial port) to run the server; `hardware_available()`
  in `hardware/executor.py` is the gate that keeps the project contributable
  without hardware.
- **Keep the UI phone-first.** The framer drives this from a phone at the
  sawhorses; test layouts narrow.
- Hardware changes: state what you tested on (controller board + firmware
  version, WiFi or USB transport) — simulation-only testing is fine for
  web/parser changes but not for burn-loop timing.
- Colorblind-safe UI: never green as a status indicator; blue vs yellow/red.

## Pull requests

- Keep PRs focused; say whether you tested in simulation, on hardware, or
  both.
- No test suite exists yet — a pytest harness around `tsj_parser.py` would be
  a very welcome first contribution.
