# deepthought

A closed-loop microscope acquisition and analysis library. Images are segmented as
they are acquired, and what the segmentation finds is available to the plan that is
still running — so the experiment can respond to the sample instead of replaying a
fixed list of coordinates.

deepthought is the client half of a two-part system. The other half is
[`hard-link`](https://github.com/ndsystems/hard-link), which puts the microscope on
the network.

## Status

**Complete, and preserved as a record.** This is research code written between 2021
and 2023 for a thesis, against the library versions of that era. It is archived at the
state that produced the results below, and is not maintained.

The architecture is the part worth reading. It is described here and analysed in full
in the accompanying [preprint](https://doi.org/10.1101/2025.02.25.639997). Current work
on the same problem continues in [gently](https://github.com/gently-project/gently).

## What it was used for

Running on an ordinary motorised widefield microscope, with no operator present:

- **22,000 cells** of immunofluorescence against γH2AX and phosphorylated Chk1
  (11,000 control, 11,000 treated with neocarzinostatin), imaged and counted
  automatically. Sample sizes at this scale normally require a high-content system.
- **12,000 cells** per condition under 0.02% MMS, where the larger N resolved a rare
  subpopulation — a shift in phosphorylated Chk1 — that was invisible at N=30.
- **24-hour live imaging** of HeLa cells expressing PCNA-chromobody, every 20 minutes.
  In an unsynchronised population, this caught PCNA repair foci being carried through
  mitosis into G1 daughter cells — an event you would otherwise need chemical cell
  cycle arrest to look for, and the arrest itself perturbs the response.

The point of all three is the same: throughput bought resolution of the population,
and the population is where the biology was.

## Architecture

Conventional microscope software is an open loop. The operator finds fields by eye,
hands the software a list of coordinates, the software returns raw data, and analysis
happens later somewhere else. If the analysis reveals drift, bad exposure, or too few
cells, the experiment is already over.

deepthought closes that loop by splitting the system across a network boundary and
putting analysis inside the acquisition:

```
  microscope PC "bright_star"                 analysis PC (any OS)
  ┌────────────────────────┐                  ┌──────────────────────────────┐
  │ devices                │                  │ deepthought                  │
  │   ↕                    │                  │                              │
  │ Micro-Manager adapters │   RPyC / TCP     │  MMCoreInterface             │
  │   ↕                    │ ←──────────────→ │    ├─ "bright_star"          │
  │ MMCore (via pymmcore)  │   :18861         │    └─ "eva_green"            │
  │   ↕                    │                  │         ↕                    │
  │ hard-link RPyC server  │                  │  bluesky plans               │
  └────────────────────────┘                  │         ↕                    │
                                              │  RunEngine                   │
  microscope PC "eva_green"                   │         ↓ documents          │
  ┌────────────────────────┐   RPyC / TCP     │  Frame → Detector → Album    │
  │ … the same stack …     │ ←──────────────→ │         ↓                    │
  └────────────────────────┘   :18861         │  live view                   │
                                              └──────────────────────────────┘
```

**Device control is a network call.** MMCore is wrapped in an RPyC server, so the
client can run on any OS and a crashing client cannot take the hardware down with it.

**One client, many microscopes.** Because a scope is just an address, a single session
holds connections to as many as you like. `MMCoreInterface` keys them by IP and by
name, and a `Microscope` is built against whichever core you hand it:

```python
scopes = MMCoreInterface()
scopes.add("10.10.1.35", "bright_star")
scopes.add("10.10.1.57", "eva_green")

m = Microscope(mmc=scopes["bright_star"])
```

This is not multiplexing one experiment across instruments — it is one place to write
plans, drive several scopes, and collect their data through the same model. Adding an
instrument is adding a line, not standing up a second software installation. It also
means a plan developed against `SimMMC` (the simulated core in `hard-link`) moves to
real hardware by changing which entry of the interface it is handed.

**Plans are separate from device commands.** Devices are described in the ophyd style
— a motor is anything you can `set` and `read`, a detector is anything you can
`trigger` and `read` — and experiments are written as bluesky plans, executed by a
RunEngine that handles sequencing, metadata, and the event stream. Camera exposure is
modelled as a motor, so an exposure sweep is written exactly like a Z scan.

**The sample is a first-class object, not a coordinate list.** A confocal dish is a
circle with a centre and a diameter; a scan grid intersected with that circle stays on
the coverslip and off the plastic periphery where the optics degrade. Sample geometry
belongs to the sample, not to the instrument.

**Analysis is inside the loop.** Each acquired image becomes a `Frame`. A `Detector`
(here, cellpose) segments it. Detected objects, their positions and intensities
accumulate in an `Album` that is live-plotted while the run continues — so the running
N is visible during acquisition, not after it.

The full design rationale, with figures, is in [`manual.tex`](manual.tex) — a thesis
chapter, and the real documentation for this repository.

## Repository map

| Module | Purpose |
|---|---|
| `devices.py` | ophyd-style Camera, Focus, XYStage, Channel, AutoFocus over MMCore; `MMCoreInterface` holds connections to several scopes |
| `microscope.py` | `BaseMicroscope` (autoexposure, channel switching, grid generation) and `Microscope` (the scan plans) |
| `run.py` | RunEngine setup, channel definitions, entry point |
| `frames.py` | `Frame`, `ObjectsCollection`, `ObjectsAlbum` — the acquired-data model |
| `detection.py` | `Detector` interface; cellpose nuclear segmentation |
| `labels.py`, `process.py` | segmentation plumbing and skimage wrappers |
| `compute.py` | circularity; fluorescence anisotropy from parallel/perpendicular channels |
| `coords.py` | conversions between `x,y`, `r,c` and Cartesian conventions — documented, standalone, the most reusable file here |
| `optimization.py` | DCT–Shannon focus metric and 1D fitting, by [@nvladimus](https://github.com/nvladimus) |
| `transform.py` | affine registration via SimpleITK/elastix |
| `comms.py` | RPyC client/server helpers |

## Running it

The intended shape was: start `hard-link` on the microscope PC, point
`MMCoreInterface` at its address, define channels, build a plan, and hand it to the
RunEngine — see `run.py`. Running it today means pinning the 2020-era dependencies it
was written against, and the hardware specifics in `run.py` are those of the
instrument it ran on.

## Accessing the example data

Two runs are included as msgpack under `deepthought/db_data/`. databroker manages
access:

1. Find where databroker looks for catalogs:
   `python -c "import databroker; print(databroker.catalog_search_path())"`
2. Copy `catalog.yml`, edit it to point at `db_data/*.msgpack`, and move it to one of
   those paths.

```python
from data import db

header = db[-1]      # a databroker.Header
df = header.table()  # as a pandas.DataFrame
```

## Citing

If this architecture is useful to you, cite the thesis chapter in `manual.tex`. The
code is MIT licensed — see [LICENSE](LICENSE).
