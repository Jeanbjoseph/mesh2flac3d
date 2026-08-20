"""
mesh2flac3d — Export meshes (Gmsh .msh, VTK, ...) to Itasca FLAC3D .f3grid,
preserving physical groups as zone groups (ZGROUP) and boundary/face groups
as face groups (FGROUP), with guaranteed right-handed (positive-volume) zones.

Reads via `meshio` (any format it supports); writes a correct FLAC3D grid.
Does NOT import `gmsh`, so it carries no GPL obligation.

Basic use:

    import mesh2flac3d as m2f
    m2f.convert("model.msh", "model.f3grid")

Copyright (c) 2026 AI SIM Engenharia Geotecnica. MIT License.
"""

from .core import convert, write_f3grid, Grid, __version__

__all__ = ["convert", "write_f3grid", "Grid", "__version__"]
