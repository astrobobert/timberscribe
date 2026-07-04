# TimberScribe Sled — Hardware Build Guide (Draft v0.1)

The sled is the self-propelled print head: a V-slot frame riding the timber on
nylon rollers, a gantry carrying a 1.6 W laser module, driven by an MKS DLC32
controller from a Kobalt 24 V tool battery. This guide covers printing the
brackets, buying the rest, and putting it together.

> **Figure H-1 — The assembled sled on a timber.**
> *[photo: full sled sitting on a squared timber, three-quarter view; callouts
> on: frame rails, gantry, laser module, controller, battery, rollers.]*

**Status: draft.** Rows marked *TBD* / *verify* need real values from the
bench. Photos land in `docs/img/`.

---

## 1. Printed parts

`3dmodels/` holds the printable parts. Convention: **`.stl` is the
print-ready truth; `.f3d`/`.f3z` is the editable Fusion 360 source** — edit
the source, re-export the STL, commit both.

| Print (`.stl`) | Qty | Source (`.f3d`) | Notes |
|---|---|---|---|
| Bridge Support | 1 *(verify)* | Bridge Supports.f3d | |
| Bridge Motor Support | 1 *(verify)* | Bridge Supports.f3d | Two prints share one source file |
| Fixed Roller Bracket A | 1 *(verify)* | Fixed Roller Bracket A.f3d | |
| Fixed Roller Bracket B | 1 *(verify)* | Fixed Roller Bracket B.f3d | |
| Float Roller Bracket AA | 1 *(verify)* | Float Roller Bracket A.f3d | AA/AB from one source *(mirrored pair? verify)* |
| Float Roller Bracket AB | 1 *(verify)* | Float Roller Bracket A.f3d | |
| Float Roller Bracket BA | 1 *(verify)* | Float Roller Bracket B.f3d | |
| Float Roller Bracket BB | 1 *(verify)* | Float Roller Bracket B.f3d | |
| Gantry to Frame Bracket | 2 *(verify)* | Gantry to Frame Bracket.f3d | |
| Gantry Limit Switch Bracket | 2 *(verify)* | Gantry Limit Switch Bracket.f3d | |
| Laser Mount | 1 | Laser Mount.f3d | |
| MKS DLC32 Bracket | 1 | MKS DLC32 Bracket.f3z | |

`Frame.f3d` is the **sled assembly file** — the whole machine modeled
together. It is not a printed part and has no STL.

Print settings *(fill in what has worked)*: material ______ , layer ______ ,
infill ______ , supports ______ .

**Still to be designed:**

| Part | Qty | Notes |
|---|---|---|
| Battery Mount | 1 | Kobalt pack cradle |
| Controller Mount / Enclosure | 1 | DLC32 + wiring bay |
| Belt Tensioner | 1 | Design, or COTS GT2 tensioner |
| Limit Switch Mounts | 2 | (gantry bracket exists; frame ends needed?) |
| Cable Clips | 2+ | |

## 2. Bill of materials

### 2.1 Frame

| Qty | Part | Status |
|---|---|---|
| 2 | V-Slot 20×40 × 400 mm | ✓ |
| 3 | V-Slot 20×40 × 200 mm | ✓ |
| 1 | V-Slot 20×20 × 500 mm | ✓ |

### 2.2 Motion system

| Qty | Part | Status |
|---|---|---|
| 1 | 17HD48002-24B stepper motor | ✓ |
| 1 | 42BL4002-24A stepper motor | ✓ |
| 2 | GT2 10 mm motor pulleys | need tooth count + bore |
| 2 | GT2 10 mm idler pulleys | need specifications |
| 1 | GT2 10 mm belt | length TBD |
| 1 | Belt tensioner | model TBD (or printed, §1) |
| 1 | Gantry trolley | model TBD |
| 8 | 25×25 mm nylon V-rollers | need supplier / part number |

### 2.3 Electronics

| Qty | Part | Status |
|---|---|---|
| 1 | MKS DLC32 V2.1 controller | ✓ |
| 1 | Creality CV 1.6 W laser module | ✓ |
| 1 | Raspberry Pi Zero 2 W (runs the TimberScribe server) | *(verify role vs DLC32 — see §4 note)* |
| 4 | Limit switches | need switch type |
| 2 | Stepper motor extension cables | TBD |
| 1 | Controller enclosure | design required (§1) |
| 1 | Wiring harness | TBD |

### 2.4 Power

| Qty | Part | Status |
|---|---|---|
| 1 | Kobalt 24 V battery | ✓ |
| 1 | Kobalt battery adapter | need source |
| 1 | 24 V voltage regulator | need exact model |
| 1 | Main fuse | rating TBD |
| 1 | Master power switch | TBD |
| 1 | Emergency stop | recommended |

### 2.5 Laser accessories

| Qty | Part | Status |
|---|---|---|
| 1 | Air assist pump | recommended |
| 1 | Air nozzle | TBD |
| 1 | Air tubing | TBD |

### 2.6 Fasteners & sundries *(the usually-missing 50–100 pieces — tally during the next assembly)*

| Qty | Part |
|---|---|
| __ | M5 T-nuts |
| __ | M5×8 socket head screws |
| __ | M5×10 socket head screws |
| __ | M5×16 socket head screws |
| __ | M3 screws |
| __ | M3 locknuts |
| __ | Spacers / washers |
| __ | Heat-set inserts (if applicable) |
| __ | Zip ties, spiral wrap / braided sleeve |

## 3. Assembly

Photo-led, one subassembly per step — shoot these during the next
build/teardown.

1. **Frame** — V-slot layout and joining.
   > *[photo: bare frame, rail lengths labeled.]*
2. **Rollers** — fixed brackets one side, floating brackets the other; how
   the float preloads against timber width variation.
   > *[photo: roller bracket pair on a rail edge, fixed vs float called out.]*
3. **Bridge / gantry** — bridge supports, trolley, gantry-to-frame brackets,
   drive belt + tensioner.
   > *[photo: gantry assembled, belt path visible.]*
4. **Laser mount** — module on the mount, air assist routing.
   > *[photo: laser mount close-up.]*
5. **Electronics + power** — DLC32 in its bracket, limit switches, battery,
   regulator, fusing, e-stop, harness routing.
   > *[photo: electronics bay, labeled.]*

## 4. Wiring

> *[photo: harness overview + a wiring diagram when the design settles.]*

*(TBD: DLC32 port map — steppers, limit switches, laser PWM, power in.)*

> **Note (to reconcile):** the server code and [README](README.md) GPIO table
> currently describe the earlier direct-GPIO drive (single motor PWM +
> encoder on the Pi via pigpio). The sled BOM above is the newer
> DLC32-based motion system. Update this section and
> `hardware/executor.py`/`config.py` docs together when that lands.

## 5. Safety

- 1.6 W diode laser: **wear the OD-rated goggles for 445 nm — always.** No
  eyes at timber level during a burn; the beam scatters off wood.
- Never leave a burn unattended; char can smolder. Keep water or an
  extinguisher at the sawhorses.
- Air assist reduces flare-ups and cleans the cut — treat it as standard
  equipment, not optional.
- E-stop within reach once fitted; until then, the master switch is the stop.
