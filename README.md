# TimberScribe — Pi Laser Print Head

**TimberScribe** is the scribing side of the **Timber Frame Suite** — an open-source
CAD/CAM system for traditional timber framers. A self-propelled laser print head
rides the timber and burns the joinery layout — mortise outlines, cut lines, bore
centers, labels — directly onto the wood. The joints themselves are still cut by
hand with traditional tools: the laser replaces tape-measure layout, not
craftsmanship.

This repository is the web server that runs on the Raspberry Pi print head.
It accepts `.tsj` job files from the framer's phone or laptop, shows a face
preview dialog, and drives the laser burn loop.

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

Start pigpio daemon (required for hardware GPIO):
```bash
sudo pigpiod
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
to a simulation mode when `pigpio` is not connected, so the full
web UI works on a dev machine without GPIO hardware.

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
│   └── executor.py       Real-time burn loop (pigpio)
├── static/
│   └── style.css         Mobile-friendly stylesheet
├── templates/
│   ├── base.html         Shared layout + status polling
│   ├── index.html        Job list + upload form
│   └── face_select.html  4-face radio dialog with SVG previews
├── data/
│   └── jobs.db           SQLite database (auto-created)
├── uploads/              Uploaded .tsj files
├── config.py             All settings (ports, GPIO pins, defaults)
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

## GPIO pins (BCM, configurable in config.py)

| Pin | Signal |
|---|---|
| 18 | Motor PWM |
| 23 | Motor direction |
| 24 | Encoder channel A |
| 25 | Encoder channel B |
| 12 | Laser PWM (hardware PWM) |
| 17 | Tape optical sensor |
