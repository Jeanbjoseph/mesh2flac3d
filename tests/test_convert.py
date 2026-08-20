"""End-to-end tests. gmsh is used ONLY to build the fixture mesh, never by the
package itself. Run: pytest -q  (needs meshio, numpy, gmsh)."""

import os
import subprocess
import sys

import numpy as np
import meshio
import pytest

import mesh2flac3d as m2f

HERE = os.path.dirname(__file__)
FIXGEN = os.path.join(HERE, "fixtures", "make_testmesh.py")


@pytest.fixture(scope="module")
def msh(tmp_path_factory):
    out = tmp_path_factory.mktemp("mesh") / "box3.msh"
    subprocess.run([sys.executable, FIXGEN, str(out)], check=True)
    return str(out)


def _read_f3grid_zones(path):
    """Minimal parser: returns points(dict id->xyz) and zones(list of node-id lists)."""
    pts, zones = {}, []
    with open(path, encoding="utf-8") as f:
        for line in f:
            s = line.split()
            if not s:
                continue
            if s[0] == "G":
                pts[int(s[1])] = np.array([float(s[2]), float(s[3]), float(s[4])])
            elif s[0] == "Z":
                zones.append([int(x) for x in s[3:]])
    return pts, zones


def _first4_positive(pts, zones):
    """Every FLAC3D zone must have its first four nodes right-handed
    (triple product > 0) — the invariant FLAC3D checks on import."""
    bad = 0
    for n in zones:
        p0, p1, p2, p3 = (pts[i] for i in n[:4])
        if np.dot(np.cross(p1 - p0, p2 - p0), p3 - p0) <= 0:
            bad += 1
    return bad


def _build_mixed_mesh():
    """In-memory mesh with wedges (W6) and a pyramid (P5), half of them
    deliberately inverted, to exercise winding correction without gmsh.
    Mirrors the case validated live in FLAC3D 7.0 (vtot == 1e6, negzero == 0)."""
    corners = np.array([[0, 0], [100, 0], [100, 100], [0, 100]], float)
    zlev = [0.0, -30.0, -60.0, -90.0]
    pts, idx = [], {}
    for k, z in enumerate(zlev):
        for c, (x, y) in enumerate(corners):
            idx[(c, k)] = len(pts)
            pts.append([x, y, z])
    pts = np.array(pts, float)
    tris = [(0, 1, 2), (0, 2, 3)]
    wedges, layer = [], []
    for k in range(3):
        for a, b, c in tris:
            wedges.append([idx[(a, k + 1)], idx[(b, k + 1)], idx[(c, k + 1)],
                           idx[(a, k)], idx[(b, k)], idx[(c, k)]])
            layer.append(k)
    wedges = np.array(wedges)
    for i in range(0, len(wedges), 2):        # invert every other wedge
        wedges[i] = wedges[i][[3, 4, 5, 0, 1, 2]]
    base_p = [idx[(0, 0)], idx[(1, 0)], idx[(2, 0)], idx[(3, 0)]]
    apex = len(pts)
    pts = np.vstack([pts, [50, 50, 30]])
    pyr = np.array([[*base_p, apex]])
    cells = [("wedge", wedges), ("pyramid", pyr)]
    sets = {}
    for k, nm in enumerate(["Overburden", "Salt", "Underburden"]):
        sets[nm] = [np.array([i for i, lk in enumerate(layer) if lk == k]),
                    np.array([], dtype=int)]
    sets["Cap"] = [np.array([], dtype=int), np.array([0])]
    return meshio.Mesh(points=pts, cells=cells, cell_sets=sets)


def test_slot_from_group_name(tmp_path):
    """A physical group named "name@slot" writes ZGROUP name in SLOT slot, so
    overlapping groups (e.g. a well cell also in the reservoir) can coexist."""
    from mesh2flac3d.core import _split_slot
    assert _split_slot("well@Well", "Default") == ("well", "Well")
    assert _split_slot("reservoir", "Default") == ("reservoir", "Default")
    assert _split_slot("a@b@c", "Default") == ("a@b", "c")

    # end-to-end: two overlapping groups in different slots
    mesh = _build_mixed_mesh()
    # rename one set to carry a slot and overlap another
    sets = dict(mesh.cell_sets)
    sets["producer@Well"] = sets["Cap"]          # pyramid, slot Well
    mesh = meshio.Mesh(points=mesh.points, cells=mesh.cells, cell_sets=sets)
    grid = m2f.Grid.from_meshio(mesh)
    out = str(tmp_path / "slots.f3grid")
    m2f.write_f3grid(grid, out)
    text = open(out, encoding="utf-8").read()
    assert 'ZGROUP "producer" SLOT "Well"' in text
    assert 'ZGROUP "Cap" SLOT "Default"' in text


def test_wedge_pyramid_winding(tmp_path):
    out = str(tmp_path / "wedp5.f3grid")
    grid = m2f.Grid.from_meshio(_build_mixed_mesh())
    m2f.write_f3grid(grid, out)
    pts, zones = _read_f3grid_zones(out)
    assert len(zones) == 7  # 6 wedges + 1 pyramid
    assert _first4_positive(pts, zones) == 0
    assert set(grid.zone_groups) == {"Overburden", "Salt", "Underburden", "Cap"}


def test_convert_preserves_groups(msh, tmp_path):
    out = str(tmp_path / "box3.f3grid")
    grid = m2f.convert(msh, out)

    # zone groups: the three volume layers must survive
    assert set(grid.zone_groups) == {"Overburden", "Salt", "Underburden"}
    # face groups: the three boundary sets must survive as FGROUP
    assert set(grid.face_groups) == {"Top", "Bottom", "Sides"}

    # every zone assigned to exactly one group (partition of the zone set)
    total_zones = sum(len(c[1]) for c in grid.zone_cells)
    grouped = np.concatenate(list(grid.zone_groups.values()))
    assert len(grouped) == total_zones
    assert len(np.unique(grouped)) == total_zones


def test_no_negative_volume_tets(msh, tmp_path):
    out = str(tmp_path / "box3.f3grid")
    m2f.convert(msh, out)
    pts, zones = _read_f3grid_zones(out)
    tets = [z for z in zones if len(z) == 4]
    assert tets, "expected tetrahedra in the fixture"
    bad = 0
    for n in tets:
        p0, p1, p2, p3 = (pts[i] for i in n)
        # FLAC3D requires positive zone volume: triple product > 0.
        # (Confirmed by FLAC3D 7.0, which errors on "tet volumes are <= 0".)
        det = np.dot(np.cross(p1 - p0, p2 - p0), p3 - p0)
        if det <= 0:
            bad += 1
    assert bad == 0, f"{bad} non-positive-volume tetrahedra written"


def test_roundtrip_with_meshio_reader(msh, tmp_path):
    """Our .f3grid must be readable back by meshio's FLAC3D reader."""
    out = str(tmp_path / "box3.f3grid")
    m2f.convert(msh, out, keep_faces=False)  # meshio reader focuses on zones
    back = meshio.read(out)
    n_tetra = sum(len(cb.data) for cb in back.cells if cb.type == "tetra")
    assert n_tetra > 0


def test_cli(msh, tmp_path):
    out = str(tmp_path / "cli.f3grid")
    dat = str(tmp_path / "cli.dat")
    rc = subprocess.run(
        [sys.executable, "-m", "mesh2flac3d.cli", msh, out, "--dat", dat],
        capture_output=True, text=True,
    )
    assert rc.returncode == 0, rc.stderr
    assert os.path.exists(out) and os.path.exists(dat)
    assert "ZGROUP" in open(out, encoding="utf-8").read()
    assert "FGROUP" in open(out, encoding="utf-8").read()
