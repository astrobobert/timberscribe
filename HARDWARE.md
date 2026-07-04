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
| Bridge Support | 1 *(verify)* | Bridge Supports.f3d | Carries a limit switch |
| Bridge Motor Support | 1 *(verify)* | Bridge Supports.f3d | Two prints share one source file; carries a limit switch |
| Fixed Roller Bracket A | 1 *(verify)* | Fixed Roller Bracket A.f3d | |
| Fixed Roller Bracket B | 1 *(verify)* | Fixed Roller Bracket B.f3d | |
| Float Roller Bracket AA | 1 *(verify)* | Float Roller Bracket A.f3d | AA/AB from one source *(mirrored pair? verify)* |
| Float Roller Bracket AB | 1 *(verify)* | Float Roller Bracket A.f3d | |
| Float Roller Bracket BA | 1 *(verify)* | Float Roller Bracket B.f3d | |
| Float Roller Bracket BB | 1 *(verify)* | Float Roller Bracket B.f3d | |
| Gantry to Frame Bracket | 2 *(verify)* | Gantry to Frame Bracket.f3d | |
| Gantry Limit Switch Bracket | 2 *(verify)* | Gantry Limit Switch Bracket.f3d | |
| Laser Mount | 1 | Laser Mount.f3d | |
| MKS DLC32 Bracket | 1 | MKS DLC32 Bracket.f3z | The controller mount |
| Tensioner_Body1 | 1 | Tensioner.f3z | Belt tensioner, piece 1 of 3 |
| Tensioner_Body2 | 1 | Tensioner.f3z | Belt tensioner, piece 2 of 3 |
| Tensioner_Body3 | 1 | Tensioner.f3z | Belt tensioner, piece 3 of 3 |

`Frame.f3d` is the **sled assembly file** — the whole machine modeled
together. It is not a printed part and has no STL.

Print settings *(fill in what has worked)*: material ______ , layer ______ ,
infill ______ , supports ______ .

**Still to be designed:**

| Part | Qty | Notes |
|---|---|---|
| Battery Mount | 1 | Kobalt pack cradle |
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
| 1 | GT2 10 mm motor pulleys, 20T, 6 mm bore | ✓ |
| 1 | GT2 10 mm idler pulleys, toothed | ✓ |
| 2 | GT2 10 mm idler pulleys, smooth | ✓ |
| 1 | GT2 10 mm belt (open, by the meter) | cut to suit — length set by the timber to be scribed |
| 1 | Belt tensioner | printed — 3-piece, §1 |
| 1 | Gantry: [V-Slot NEMA 17 belt-driven linear actuator bundle](https://www.ebay.com/itm/405009993772?var=675070040219) (prebuilt) | ✓ — stock tensioner swapped for the printed one (§1) |
| 8 | 25×25 mm nylon V-rollers (uxcell; 686Z roller bearings, 6 mm bore) | ✓ |
| 8 *(verify qty)* | 5.9 mm axle rods | slip fit through the 6 mm bearing bore |

### 2.3 Electronics

| Qty | Part | Status |
|---|---|---|
| 1 | MKS DLC32 V2.1 controller | ✓ |
| 1 | Creality CV 1.6 W laser module | ✓ |
| 1 | Raspberry Pi Zero 2 W (runs the TimberScribe server) | *(verify role vs DLC32 — see §4 note)* |
| 4 | Limit switches | 2 on the gantry brackets, 2 on the bridge supports; need switch type |
| 2 | Stepper motor extension cables | TBD |
| 1 | Controller mount | printed — MKS DLC32 Bracket, §1 |
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
3. **Bridge / gantry** — the gantry arrives as a prebuilt belt-driven
   actuator (§2.2): swap its stock tensioner for the printed 3-piece one,
   then mount via the bridge supports and gantry-to-frame brackets.
   > *[photo: gantry assembled, belt path visible, printed tensioner called
   > out.]*
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
