# TimberScribe — Laser Print Head Server

**TimberScribe** is the scribing side of the **Timber Frame Suite** — an open-source
CAD/CAM system for traditional timber framers. A self-propelled laser print head
rides the timber and burns the joinery layout — mortise outlines, cut lines, bore
centers, labels — directly onto the wood. The joints themselves are still cut by
hand with traditional tools: the laser replaces tape-measure layout, not
craftsmanship.

This repository is the web server that drives the print head. It runs on any
laptop joined to the sled's WiFi hotspot, accepts `.tsj` job files from the
framer's phone or laptop, shows a face preview dialog, and streams g-code
over WiFi to the sled's GRBL controller (an MKS DLC32 V2.2 running
[FluidNC](https://github.com/bdring/FluidNC) — the controller hosts the hotspot, so
nothing rides the sled but the controller itself).

`.tsj` jobs are produced by the [TimberDraw](https://github.com/astrobobert/timberdraw)
AutoCAD plugin's scribe export (`TScribe` / `TScribeAll`) — one file per timber face,
with profile linework, cut-to-length lines, depth/bevel labels, and peg bores.
The file format is specified in [TSJ_SPEC.md](TSJ_SPEC.md); `app/tsj_parser.py`
is its reference validator. Building the sled itself — printed parts, BOM,
assembly — is covered in [HARDWARE.md](HARDWARE.md).

---

## Setup

On the machine that will run the server (the shop laptop):

```bash
cd TimberScribe
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Power the sled and join this machine to the controller's WiFi hotspot
(FluidNC AP mode — SSID and address in `config.py`: `GRBL_AP_SSID`,
`GRBL_HOST`). Firmware flashing and hotspot configuration are covered in
[HARDWARE.md](HARDWARE.md) §4.

Run the server:
```bash
python run.py
```

Open on a phone joined to the same hotspot:
```
http://<laptop-ip>:5000
```

> Note: while joined to the sled's hotspot the laptop has no internet —
> that's normal at the sawhorses.

A bench fallback over USB serial still exists: set
`GRBL_TRANSPORT = "serial"` and `SERIAL_PORT` in `config.py` and plug the
DLC32 into USB.

---

## Development

Run with auto-reload:
```bash
flask --app run:app run --debug --host 0.0.0.0 --port 5000
```

The hardware layer (`hardware/executor.py`) gracefully falls back to a
simulation mode when the GRBL controller is unreachable (no sled hotspot,
no serial port), so the full web UI works on a dev machine without the
sled. Simulated completions are labeled as such in the job status.

---

## Project layout

```
TimberScribe/
├── app/
│   ├── __init__.py       Flask app factory
│   ├── routes.py         HTTP endpoints
│   ├── job_store.py      SQLite job queue
│   ├── tsj_parser.py     .tsj file validation and parsing
│   └── executor.py       Background print thread
├── hardware/
│   ├── __init__.py
│   ├── executor.py       GRBL g-code sender (WiFi / USB serial)
│   └── fluidnc/
│       ├── config.yaml   The controller's FluidNC config (source of truth)
│       └── upload_config.py  Bench tool: push config.yaml to the board over USB
├── static/
│   └── style.css         Mobile-friendly stylesheet
├── templates/
│   ├── base.html         Shared layout + status polling
│   ├── index.html        Job list + upload form
│   └── face_select.html  4-face radio dialog with SVG previews
├── data/
│   └── jobs.db           SQLite database (auto-created)
├── uploads/              Uploaded .tsj files
├── config.py             All settings (network, transport, burn defaults)
├── run.py                Entry point
└── requirements.txt
```

---

## API endpoints

| Method | URL | Description |
|---|---|---|
| GET | `/` | Job list + upload form |
| POST | `/upload` | Receive .tsj file |
| GET | `/job/<id>` | Face selector dialog |
| POST | `/job/<id>/select` | Save face selection + settings |
| POST | `/job/<id>/print` | Queue for printing |
| GET | `/job/<id>/delete` | Delete job |
| GET | `/status` | Current print status (JSON) |
| GET | `/status/<id>` | Specific job status (JSON) |

---

## Architecture

The laptop is the server; the DLC32 is the motion controller *and* the
WiFi access point. Everything joins the sled's hotspot:

```
phone (browser) ──┐
                  │  sled's WiFi hotspot (FluidNC AP mode)
                  ▼
   shop laptop — this Flask server
                  │  raw g-code over TCP :23 (FluidNC telnet)
                  ▼
        MKS DLC32 V2.2 (FluidNC)
                  │
   ┌──────────────┼───────────────────┐
   ▼              ▼                   ▼
gantry stepper   bridge drive       laser PWM
(cross axis,     stepper (along     (1.6 W Creality)
carries laser)   the timber)      + 4 limit switches
```

Transport, host, and port live in `config.py` (`GRBL_TRANSPORT`,
`GRBL_HOST`, `GRBL_TCP_PORT`); USB serial remains as a bench fallback.
Earlier iterations used a 3018 Woodpecker GRBL board, then a DLC32 fed
g-code over USB by a Raspberry Pi riding the sled — the DLC32 V2.2's
onboard WiFi retired the Pi. The DLC32 port map (steppers, limit
switches, laser PWM, power in) is still TBD — see
[HARDWARE.md](HARDWARE.md) §4.
