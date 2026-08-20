# Example — 30-second quickstart

A ready-to-use Gmsh mesh so you can try `mesh2flac3d` without building one first.

`three_layer_box.msh` is a 100 x 100 x 90 box split into three horizontal
layers, with named physical groups:

- **Volumes:** `Overburden`, `Salt`, `Underburden`  → become FLAC3D zone groups
- **Surfaces:** `Top`, `Bottom`, `Sides`            → become FLAC3D face groups

## 1. Install

```bash
pip install mesh2flac3d
```

## 2. Convert

```bash
mesh2flac3d three_layer_box.msh three_layer_box.f3grid
```

Expected output:

```
[mesh2flac3d] three_layer_box.msh -> three_layer_box.f3grid
  points: 350  zones: 1218  faces: 522
  zone groups: Underburden(401), Salt(414), Overburden(403)
  face groups: Top(90), Bottom(90), Sides(342)
```

## 3. Import in FLAC3D

```
model new
zone import 'three_layer_box.f3grid'
zone list group          ; see Overburden / Salt / Underburden
```

The grid imports with **zero negative-volume zones** and total volume
`900000` (= 100 x 100 x 90), matching the geometry exactly.

## Regenerate the mesh (optional)

Two equivalent sources are provided — both produce the same mesh:

**Gmsh `.geo` script** (native Gmsh, no Python):

```bash
gmsh three_layer_box.geo -3 -o three_layer_box.msh
```

**Python script** (Gmsh API):

```bash
pip install gmsh
python generate_example_mesh.py three_layer_box.msh
```

## Use your own mesh

In Gmsh, give your regions and boundaries **named** physical groups — those
names carry through to FLAC3D:

```
Physical Volume("Salt")  = {2};
Physical Surface("Top")  = {4};
```
