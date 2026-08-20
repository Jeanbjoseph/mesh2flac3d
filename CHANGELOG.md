# Changelog

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
