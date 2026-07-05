# TimberScribe — Pi Laser Print Head

**TimberScribe** is the scribing side of the **Timber Frame Suite** — an open-source
CAD/CAM system for traditional timber framers. A self-propelled laser print head
rides the timber and burns the joinery layout — mortise outlines, cut lines, bore
centers, labels — directly onto the wood. The joints themselves are still cut by
hand with traditional tools: the laser replaces tape-measure layout, not
craftsmanship.

This repository is the web server that runs on the Raspberry Pi print head.
It accepts `.tsj` job files from the framer's phone or laptop, shows a face
preview dialog, and streams g-code to the sled's GRBL controller.

`.tsj` jobs are produced by the [TimberDraw](https://github.com/astrobobert/timberdraw)
AutoCAD plugin's scribe export (`TScribe` / `TScribeAll`) — one file per timber face,
with profile linework, cut-to-length lines, depth/bevel labels, and peg bores.
The file format is specified in [TSJ_SPEC.md](TSJ_SPEC.md); `app/tsj_parser.py`
is its reference validator. Building the sled itself — printed parts, BOM,
assembly — is covered in [HARDWARE.md](HARDWARE.md).

---

## Setup on the Pi

```bash
cd ~/TimberScribe
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Plug the GRBL controller (MKS DLC32) into the Pi's USB and give your user
serial-port access (once, then log out/in):
```bash
sudo usermod -a -G dialout $USER
ls /dev/ttyUSB0        # confirm the controller enumerated
```

Run the server:
```bash
python run.py
```

Open on a phone/laptop connected to the same network:
```
http://<pi-ip-address>:5000
```

---

## Development on Windows (VS Code Remote SSH)

Connect VS Code to the Pi via Remote SSH, open `~/TimberScribe`.

Run with auto-reload:
```bash
flask --app run:app run --debug --host 0.0.0.0 --port 5000
```

The hardware layer (`hardware/executor.py`) gracefully falls back
to a simulation mode when no GRBL controller is present on
`config.SERIAL_PORT`, so the full web UI works on a dev machine
without the sled attached.

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
│   └── executor.py       GRBL g-code sender (USB serial)
├── static/
│   └── style.css         Mobile-friendly stylesheet
├── templates/
│   ├── base.html         Shared layout + status polling
│   ├── index.html        Job list + upload form
│   └── face_select.html  4-face radio dialog with SVG previews
├── data/
│   └── jobs.db           SQLite database (auto-created)
├── uploads/              Uploaded .tsj files
├── config.py             All settings (ports, serial, burn defaults)
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

The Pi is the server, not the motion controller:

```
phone/laptop ──WiFi──▶ Pi (this Flask server)
                        │  g-code over USB serial, 115200 baud
                        ▼
              MKS DLC32 V2.1 (GRBL)
                        │
        ┌───────────────┼───────────────────┐
        ▼               ▼                   ▼
  gantry stepper   bridge drive       laser PWM
  (cross axis,     stepper (along     (1.6 W Creality)
  carries laser)   the timber)      + 4 limit switches
```

Serial port and baud live in `config.py` (`SERIAL_PORT`, `SERIAL_BAUD`).
The earlier bench prototype used a 3018 Woodpecker GRBL board; the DLC32
supersedes it. The DLC32 port map (steppers, limit switches, laser PWM,
power in) is still TBD — see [HARDWARE.md](HARDWARE.md) §4.
