# TimberScribe — Laser Print Head Server

**TimberScribe** is the scribing side of the **Timber Frame Suite** — an open-source
CAD/CAM system for traditional timber framers. A self-propelled laser print head
rides the timber and burns the joinery layout — mortise outlines, cut lines, bore
centers, labels — directly onto the wood. The joints themselves are still cut by
hand with traditional tools: the laser replaces tape-measure layout, not
craftsmanship.

This repository is the web server that drives the print head. It runs on a
shop server — a plugged-in Raspberry Pi or any laptop on the same network as
the sled — accepts `.tsj` job files from the framer's phone, shows a face
preview dialog, and streams g-code over WiFi to the sled's GRBL controller
(an MKS DLC32 V2.2 running
[FluidNC](https://github.com/bdring/FluidNC); nothing rides the sled but the
controller itself). It also exports `.gcode` files for running from the
controller's SD card when there's no server around — see "Two ways to run a
burn" below.

`.tsj` jobs are produced by the [TimberDraw](https://github.com/astrobobert/timberdraw)
AutoCAD plugin's scribe export (`TScribe` / `TScribeAll`) — one file per timber face,
with profile linework, cut-to-length lines, depth/bevel labels, and peg bores.
The file format is specified in [TSJ_SPEC.md](TSJ_SPEC.md); `app/tsj_parser.py`
is its reference validator. Building the sled itself — printed parts, BOM,
assembly — is covered in [HARDWARE.md](HARDWARE.md).

---

## Two ways to run a burn

**Shop mode (streamed):** the sled joins the shop WiFi (FluidNC station
mode), this server runs on a machine on the same network — a plugged-in
Raspberry Pi (below) or any laptop — and your phone drives the web UI:
upload, preview, adjust, print. G-code streams live to the controller
at `fluidnc.local` (TCP 23), with per-entity status on the phone.

**Field mode (SD card):** out of router range the sled automatically
falls back to broadcasting its own hotspot, and no server is needed at
all. Export a `.gcode` file ahead of time — the **Export .gcode**
button on the face page, or `python export_gcode.py <file.tsj>` — get
it onto your phone, join the sled's hotspot, upload the file to the
controller's SD card through the board's own web page, and run it from
there. A card-run burn doesn't need WiFi once started. (The card:
4–16 GB, FAT32.)

Firmware flashing, WiFi setup, and homing are covered in
[HARDWARE.md](HARDWARE.md) §4. A bench fallback over USB serial also
exists: set `GRBL_TRANSPORT = "serial"` and `SERIAL_PORT` in
`config.py` and plug the DLC32 into USB.

## Setup (any server machine)

```bash
cd TimberScribe
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python run.py
```

Open on a phone on the same network:
```
http://<server-ip>:5000
```

## Shop server on a Raspberry Pi

A Pi plugged in on the shop network makes the server an appliance — no
laptop in the workflow. One-time setup on the Pi:

```bash
git clone https://github.com/astrobobert/timberscribe.git ~/TimberScribe
cd ~/TimberScribe
python -m venv .venv
.venv/bin/pip install -r requirements.txt

# Start on every boot:
sed "s|USER|$(whoami)|g" deploy/timberscribe.service | \
  sudo tee /etc/systemd/system/timberscribe.service
sudo systemctl enable --now timberscribe
```

Then browse to `http://<pi-ip>:5000` from the phone — give the Pi a
reserved address in the router and bookmark it. `fluidnc.local`
resolution works out of the box on Raspberry Pi OS (avahi). Logs:
`journalctl -u timberscribe -f`.

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
