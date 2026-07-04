# TSJ_SPEC — The TimberScribe Job Format, v2.0

A `.tsj` file describes the laser burn job for **one face of one timber**: the
linework to scribe, the machine settings to scribe it with, and a preview for
the operator. It is plain **JSON**, `snake_case` keys, all dimensions in
**inches**, encoded **UTF-8 without BOM** (the parser rejects a BOM).

This document is the canonical spec. The reference implementations are:

- **Producer:** `ScribeTsj.cs` in the
  [timberdraw](https://github.com/astrobobert/timberdraw) repo
  (`Managed/ScribeTsj.cs`) — the active writer. The legacy TimberTag
  `TsjWriter` produced the same schema; files from either burn identically.
- **Consumer:** `app/tsj_parser.py` in this repo (validation) and
  `hardware/executor.py` (the burn loop).

**Any schema change must touch the writer AND the parser in the same change.**

---

## File naming

One file per side face, named `<stem>_faceN.tsj` with `N` = 1–4:

- Principal timbers: the stem is the sanitized location label —
  `P-2A_face1.tsj`.
- Repetitive families (braces, joists, commons, purlins) export one set per
  unique geometry: `<Family>_<W>x<D>[_xCOUNT]_faceN.tsj` —
  `Brace_4x5_x12_face1.tsj` means *cut twelve of these*.
- Spaces and filesystem-invalid characters are replaced with `_`.

Only faces that carry marks are written; a timber may ship fewer than 4 files.

## Coordinate system

Per face, as the laser sees the timber:

- **Origin** — the face's **upper-left corner**: the datum edge (reference
  arris) at the anchor end.
- **X** — along the timber's length; anchor end = 0, increasing toward the
  far end.
- **Y** — across the face, **downward** (toward the framer); datum edge = 0.
- **Units** — inches, decimal.
- **Angles** — degrees. Arc sweeps run counter-clockwise from `start_angle_deg`
  to `end_angle_deg` *in this y-down frame*.

The face numbering (RS1–RS4) and datum-first shop practice are described in
the TimberDraw user guide (ch. 13); this file only fixes the geometry
contract.

## Top-level structure

```json
{
  "tsj_version": "2.0",
  "generated":   "2026-07-04T18:20:00.0000000Z",
  "timber":      { ... },
  "face":        { ... },
  "settings":    { ... },
  "entities":    [ ... ],
  "preview_svg": "<svg ...>...</svg>"
}
```

| Field | Type | Required | Notes |
|---|---|---|---|
| `tsj_version` | string | yes | `"2.0"`. The parser accepts any `2.x`. |
| `generated` | string | no | ISO-8601 UTC timestamp of export. |
| `timber` | object | yes | Identity + overall dimensions (below). |
| `face` | object | yes | Which face and its extents (below). |
| `settings` | object | no | Machine profiles; consumer defaults apply if absent. |
| `entities` | array | yes (may be empty) | The burn geometry (below). |
| `preview_svg` | string | no | Inline SVG for the face-selector UI; a placeholder is synthesized if absent. |

Optional/null fields are **omitted** by the writer, not emitted as `null`.

### `timber`

| Field | Type | Required | Notes |
|---|---|---|---|
| `id` | string | yes, non-empty | The timber's location label (or family stem for repeats). |
| `description` | string | no | Free text shown in the job list. |
| `length_in` | number > 0 | yes | Overall length. |
| `width_in` | number > 0 | yes | Section width. |
| `height_in` | number | no | Section depth. |
| `species` | string | no | Reserved; not currently written. |

### `face`

| Field | Type | Required | Notes |
|---|---|---|---|
| `number` | int 1–4 | yes | RS face number. The parser rejects anything else. |
| `length_in` | number > 0 | yes | Face extent in X. |
| `width_in` | number > 0 | yes | Face extent in Y. |
| `origin`, `x_axis`, `y_axis` | string | no | Human-readable descriptions of the coordinate frame. **Informative only** — consumers must not parse them. |

### `settings`

Two machine profiles. All values are operator-adjustable on the Pi before
printing; the file's values are starting points.

```json
"settings": {
  "scribe": { "feed_in_per_min": 32,  "laser_power_pct": 70, "passes": 1 },
  "travel": { "feed_in_per_min": 118, "laser_power_pct": 0 }
}
```

| Field | Default | Meaning |
|---|---|---|
| `scribe.feed_in_per_min` | 32 | Head speed while burning. |
| `scribe.laser_power_pct` | 70 | Laser power while burning, 0–100. |
| `scribe.passes` | 1 | Repeat count per entity. |
| `travel.feed_in_per_min` | 118 | Head speed between entities, laser off. |
| `travel.laser_power_pct` | 0 | Must be 0. |
| `*.description` | — | Informative only. |

## Entities

Each entity is one burnable mark. `type` is required; the burn loop **skips
unknown types with a log line** (forward compatibility — additive types don't
break old firmware).

Only *burnable* geometry appears here. Text (labels, depths, bevels, the
blind-peg `B`) is pre-stroked by the producer into `line`/`polyline` entities
— **the format has no text entity** and consumers need no fonts. Hidden /
boundary linework appears only in the preview SVG, never in `entities`.

### `line`

```json
{ "type": "line", "start": [x, y], "end": [x, y] }
```

### `polyline`

```json
{ "type": "polyline", "closed": true, "points": [[x, y], [x, y], ...] }
```

When `closed` is true, the burner returns to `points[0]` after the last point;
the closing point is **not** repeated in `points`.

### `circle`

```json
{ "type": "circle", "center": [x, y], "radius_in": 0.5, "scribe_center": true }
```

Peg bores. With `scribe_center` true the burner marks a center cross first,
then traces the outline — the framer drills to the cross.

### `arc`

```json
{ "type": "arc", "center": [x, y], "radius_in": 2.0,
  "start_angle_deg": 0, "end_angle_deg": 90 }
```

Sweep is counter-clockwise from start to end angle in the face's y-down frame.

## `preview_svg`

A complete inline `<svg>` document, `viewBox` in face inches, rendered by the
face-selector UI. It shows more than the burn set, styled so cut-vs-context
reads at a glance (colorblind-safe — no green):

- **Burned cut lines** — solid black, heavier stroke.
- **Stock boundary** (face outline, not burned) — solid gray.
- **Preview-only marks** (hidden linework) — dashed blue.
- **Anchor marker** — an orange circle-and-cross at the origin.

Consumers must treat the SVG as opaque display content; the burn truth is
`entities` only.

## Validation contract

What `app/tsj_parser.py` enforces (`TsjError`, job rejected):

- File readable, valid JSON, **no BOM**.
- `tsj_version` starts with `2.`.
- `timber` present; `timber.id` non-empty; `timber.length_in` / `width_in`
  positive numbers.
- `face` present; `face.number` in 1–4; `face.length_in` / `width_in`
  positive numbers.
- `entities` is a list; every entity has a `type`.

Warning only (job accepted, logged):

- Any coordinate outside the face bounds by more than **0.5"** — usually a
  projection bug in the producer; the operator sees it in the log.

Missing `settings` fall back to the defaults above. A missing `preview_svg`
gets a gray "No preview" placeholder.

## Minimal example

A 10' × 8" face with one cut-to-length line, a mortise outline, and a peg
bore:

```json
{
  "tsj_version": "2.0",
  "generated": "2026-07-04T18:20:00.0000000Z",
  "timber": { "id": "TG-2", "length_in": 120.0, "width_in": 8.0, "height_in": 10.0 },
  "face":   { "number": 1, "length_in": 120.0, "width_in": 8.0 },
  "settings": {
    "scribe": { "feed_in_per_min": 32, "laser_power_pct": 70, "passes": 1 },
    "travel": { "feed_in_per_min": 118, "laser_power_pct": 0 }
  },
  "entities": [
    { "type": "line", "start": [4.0, 0.0], "end": [4.0, 8.0] },
    { "type": "polyline", "closed": true,
      "points": [[56.0, 3.0], [64.0, 3.0], [64.0, 5.0], [56.0, 5.0]] },
    { "type": "circle", "center": [60.0, 4.0], "radius_in": 0.5, "scribe_center": true }
  ],
  "preview_svg": "<svg viewBox=\"0 0 120.000 8.000\" xmlns=\"http://www.w3.org/2000/svg\">...</svg>"
}
```

## Version history

- **2.0** — current. Introduced by TimberTag's `TsjWriter`; TimberDraw's
  managed exporter (`Managed/ScribeTsj.cs`) writes the identical schema.
  Consumers should accept any `2.x` and skip unknown entity types; producers
  bumping the minor version must stay additive.
