# mesh2flac3d

Convert meshes (Gmsh `.msh`, VTK, and anything [meshio](https://github.com/nschloe/meshio) reads) to **Itasca FLAC3D** `.f3grid` grids — **preserving physical groups**:

- **Volume** physical groups → **`ZGROUP`** (zone groups)
- **Surface** physical groups → **`FGROUP`** (face groups, for boundary conditions)
- **Correct zone winding**: every zone is reordered to FLAC3D's convention, so you never get *negative-volume zone* errors on import.

It reads meshes through `meshio` (MIT) and **does not import `gmsh`**, so it carries no GPL obligation — you can use it freely, including in commercial workflows.

## Why not just use meshio?

`meshio` has a FLAC3D writer, but for a typical geomechanics mesh (volume **and** surface physical groups) it currently:

- **crashes** (`TypeError` in `split_f_z`) when both zone and face groups are present, and
- **drops all 2D groups** (`"FLAC3D format only supports 3D cells. Skipping triangle…"`), so you lose the face groups you need for boundary conditions, and
- does not guarantee zone orientation.

`mesh2flac3d` is a focused, correct writer built for that exact case.

## Install

```bash
pip install mesh2flac3d          # once published
# or, from source:
pip install -e .
```

## Command line

```bash
mesh2flac3d model.msh model.f3grid
mesh2flac3d model.msh                 # -> model.f3grid
mesh2flac3d model.msh out.f3grid --dat out.dat   # also write a FLAC3D command skeleton
mesh2flac3d model.msh --no-faces      # zones only
```

Example output:

```
[mesh2flac3d] model.msh -> model.f3grid
  points: 350  zones: 1218  faces: 522
  zone groups: Underburden(401), Salt(414), Overburden(403)
  face groups: Top(90), Bottom(90), Sides(342)
```

## Python API

```python
import mesh2flac3d as m2f

grid = m2f.convert("model.msh", "model.f3grid")
print(grid.zone_groups.keys())   # dict_keys(['Underburden', 'Salt', 'Overburden'])
print(grid.face_groups.keys())   # dict_keys(['Top', 'Bottom', 'Sides'])
```

## Supported elements

| Family | Gmsh / meshio          | FLAC3D |
|--------|------------------------|--------|
| Zones  | tetra                  | T4     |
|        | pyramid                | P5     |
|        | wedge / prism          | W6     |
|        | hexahedron             | B8     |
| Faces  | triangle               | T3     |
|        | quad                   | Q4     |

High-order variants (tetra10, hexahedron20, …) are exported using their linear
corner nodes.

## In Gmsh, name your groups

Give your regions and boundaries **Physical Groups** with names — those names
become the FLAC3D group names:

```
Physical Volume("Salt")  = {2};
Physical Surface("Top")  = {4};
```

## Development

```bash
pip install -e ".[test]"
pytest -q
```

The test fixture is generated with Gmsh (`tests/fixtures/make_testmesh.py`);
Gmsh is a **test-only** dependency, never used by the package at runtime.

## License

MIT © AI SIM Engenharia Geotécnica. FLAC3D and Itasca are trademarks of Itasca
Consulting Group; this project is independent and not affiliated with Itasca.
