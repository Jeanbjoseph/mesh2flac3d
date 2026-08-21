# Dean (2006) SPE-79709 benchmark meshes

Reservoir-geomechanics meshes from **Dean, Gai, Stone & Minkoff (2006),
"A Comparison of Techniques for Coupling Porous Flow and Geomechanics",
SPE Journal 11(1), SPE-79709**. These are standard coupled-flow/geomechanics
benchmark grids — provided here as realistic `mesh2flac3d` examples.

All meshes are **SI (metres)**, hexahedral, `z = 0` at the top and `z < 0`
downward. Problems 1 and 2 share the same grid (they differ in boundary
conditions, not geometry).

| File | Problem | Grid | Zones | Groups |
|------|---------|------|-------|--------|
| `problem_1_2.geo` | 1 & 2 — subsidence over a producing reservoir | 11×11×10 uniform | 1210 | `reservoir` (Region), `well` (Well) |
| `problem_3.geo`   | 3 — soft reservoir in stiffer non-pay rock  | 21×21×12 variable | 5292 | `overburden`/`payband`/`underburden` (Rock), `reservoir` (Region), `well` (Well) |
| `problem_4.geo`   | 4 — quarter five-spot (injector/producer)   | 21×21×11 uniform | 4851 | `layer01…layer11` (Layer), `well_inj`/`well_prod` (Well) |

## Run any of them

The meshed `.msh` files are **included**, so no meshing tool is required —
just convert:

```bash
mesh2flac3d problem_1_2.msh problem_1_2.f3grid --check
```

`--check` computes every zone volume and exits non-zero if any is
non-positive, so you can confirm the grid is FLAC3D-ready without opening
FLAC3D. Then in FLAC3D: `zone import 'problem_1_2.f3grid'`.

Each grid imports into FLAC3D 7 with **zero negative-volume zones** and the
group counts above.

To regenerate a `.msh` after editing its `.geo` (needs gmsh):

```bash
gmsh problem_1_2.geo -3 -o problem_1_2.msh
```

## Slots — how overlapping groups are kept

Real reservoir grids put a cell in several groups at once: a well cell is also
part of a reservoir and of a geological layer. FLAC3D handles this with
**slots** (one group per slot per zone). `mesh2flac3d` reads a slot from the
physical-group name using the `name@slot` convention:

```
Physical Volume("well@Well")        = { ... };   // -> ZGROUP "well"      SLOT "Well"
Physical Volume("reservoir@Region") = { ... };   // -> ZGROUP "reservoir" SLOT "Region"
```

Because the two live in different slots, the well cells stay part of the
reservoir. A name without `@` uses the default slot. In FLAC3D you then target
each independently, e.g. `zone cmodel assign elastic range group 'reservoir' slot 'Region'`.

## Attribution

The benchmark is defined in Dean et al. (2006), SPE-79709. These `.geo` files
are an independent reconstruction of the benchmark geometry for meshing
demonstrations; they are not affiliated with or endorsed by the authors or SPE.
