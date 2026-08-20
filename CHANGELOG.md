# Changelog

## 0.2.0 — 2026-08-20

- **Slots**: a physical group named `name@slot` is written as `ZGROUP/FGROUP
  "name" SLOT "slot"`, so overlapping groups (a well cell that is also in a
  reservoir and a layer) coexist — FLAC3D keeps one group per slot per zone.
- Read physical groups from `gmsh:physical` cell data as a fallback when a
  reader does not populate `cell_sets` (e.g. legacy MSH 2.2).
- Added the **Dean (2006) SPE-79709** benchmark meshes (problems 1–4) under
  `examples/dean/`, validated on FLAC3D 7.0.

## 0.1.0 — 2026-08-20

First release.

- Convert any [meshio](https://github.com/nschloe/meshio)-readable mesh
  (Gmsh `.msh`, VTK, …) to Itasca FLAC3D `.f3grid`.
- Preserve volume physical groups as `ZGROUP` and surface physical groups as
  `FGROUP` (for boundary conditions).
- Guarantee positive-volume zones via automatic winding correction for T4, B8,
  W6 and P5 elements.
- CLI (`mesh2flac3d`) and Python API (`mesh2flac3d.convert`).
- Optional FLAC3D command-file (`.dat`) skeleton generator.
- Does not import `gmsh`, so no GPL obligation.

Validated on FLAC3D 7.0: tetra, hexahedron, wedge and pyramid grids import with
zero negative-volume zones and correct total volume, with zone and face groups
recognized.
