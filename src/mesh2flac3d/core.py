"""Core conversion logic: meshio Mesh -> FLAC3D .f3grid.

The FLAC3D grid (.f3grid) ASCII format used here:

    * GRIDPOINTS
    G <gid> <x> <y> <z>
    * ZONES
    Z <T4|W6|P5|B8> <zid> <n1> <n2> ...
    * ZONE GROUPS
    ZGROUP "<name>" SLOT <slot>
      <zid> <zid> ...
    * FACES
    F <T3|Q4> <fid> <n1> <n2> ...
    * FACE GROUPS
    FGROUP "<name>" SLOT <slot>
      <fid> <fid> ...

Node/zone/face IDs are 1-based. Zones and faces have independent ID spaces.
Zone connectivity is reordered so the first four corner nodes form a
right-handed system (positive volume) — FLAC3D rejects inverted zones.
"""

from __future__ import annotations

import numpy as np

__version__ = "0.2.0"

# meshio cell type -> FLAC3D keyword
MESHIO_TO_FLAC3D_TYPE = {
    "tetra": "T4",
    "pyramid": "P5",
    "wedge": "W6",
    "hexahedron": "B8",
    "triangle": "T3",
    "quad": "Q4",
}

# 3D (zone) vs 2D (face) meshio types, mapping any high-order variant to its
# linear corner topology (we export corner nodes only).
ZONE_TYPES = {
    "tetra": "tetra", "tetra10": "tetra",
    "pyramid": "pyramid", "pyramid13": "pyramid",
    "wedge": "wedge", "wedge12": "wedge", "wedge15": "wedge", "wedge18": "wedge",
    "hexahedron": "hexahedron", "hexahedron20": "hexahedron",
    "hexahedron24": "hexahedron", "hexahedron27": "hexahedron",
}
FACE_TYPES = {
    "triangle": "triangle", "triangle6": "triangle", "triangle7": "triangle",
    "quad": "quad", "quad8": "quad", "quad9": "quad",
}

# Node reordering meshio -> FLAC3D, and the mirror ordering used when the first
# variant yields a left-handed (negative) zone.
ORDER = {
    "tetra": [0, 1, 2, 3],
    "pyramid": [0, 1, 3, 4, 2],
    "wedge": [0, 1, 3, 2, 4, 5],
    "hexahedron": [0, 1, 3, 4, 2, 7, 5, 6],
}
ORDER_MIRROR = {
    "tetra": [0, 2, 1, 3],
    "pyramid": [0, 3, 1, 4, 2],
    "wedge": [0, 2, 3, 1, 5, 4],
    "hexahedron": [0, 3, 1, 4, 2, 5, 7, 6],
}

# cell_set keys produced by meshio readers that are not real physical groups.
_INTERNAL_SET_PREFIXES = ("gmsh:", "medit:", "cell_set-")


def _is_internal_key(key: str) -> bool:
    return any(key.startswith(p) for p in _INTERNAL_SET_PREFIXES)


def _reorder_zone(points, conn, key):
    """Reorder one block of zone connectivity to right-handed FLAC3D order.

    `conn` is (n, k) corner indices into `points`; `key` is the linear type.
    FLAC3D requires each zone to have positive volume: the first four corner
    nodes must form a right-handed system, i.e. the scalar triple product
    (p1-p0)x(p2-p0)-(p3-p0) > 0. (Verified against FLAC3D 7.0, which rejects a
    grid with "tet volumes are <= 0" otherwise.) Returns (n, k) reordered so
    every zone imports without a negative-volume error.
    """
    o1 = ORDER[key]
    o2 = ORDER_MIRROR[key]
    reordered = conn[:, o1]
    p = points[reordered[:, :4]]
    a = p[:, 1] - p[:, 0]
    b = p[:, 2] - p[:, 0]
    c = p[:, 3] - p[:, 0]
    det = np.einsum("ij,ij->i", np.cross(a, b), c)
    # keep o1 where it already yields positive volume (det > 0); else mirror it
    out = np.where((det > 0)[:, None], conn[:, o1], conn[:, o2])
    return out


class Grid:
    """A FLAC3D grid ready to be written.

    Built from a meshio Mesh. Splits cells into zones (3D) and faces (2D),
    fixes zone winding, and resolves physical groups into zone/face groups
    keyed by name.
    """

    def __init__(self, points, zone_cells, face_cells, zone_groups, face_groups):
        self.points = points                # (npts, 3) float
        self.zone_cells = zone_cells        # list of (flac3d_type, (n,k) int, base_id)
        self.face_cells = face_cells        # list of (flac3d_type, (n,k) int, base_id)
        self.zone_groups = zone_groups      # {name: np.array of 1-based zone ids}
        self.face_groups = face_groups      # {name: np.array of 1-based face ids}

    @classmethod
    def from_meshio(cls, mesh, keep_faces=True):
        points = np.asarray(mesh.points, dtype=float)
        if points.shape[1] == 2:  # promote 2D coords to 3D
            points = np.column_stack([points, np.zeros(len(points))])

        # Assign global 1-based ids per block; map block index -> id offset.
        zone_cells, face_cells = [], []
        zone_block_base = {}   # block_index -> first zone id (1-based)
        face_block_base = {}
        zid = 0
        fid = 0
        for bi, cb in enumerate(mesh.cells):
            ct = cb.type
            data = np.asarray(cb.data)
            if ct in ZONE_TYPES:
                key = ZONE_TYPES[ct]
                corners = data[:, : len(ORDER[key])]
                conn = _reorder_zone(points, corners, key)
                zone_block_base[bi] = zid + 1
                zone_cells.append((MESHIO_TO_FLAC3D_TYPE[key], conn, zid + 1))
                zid += len(conn)
            elif keep_faces and ct in FACE_TYPES:
                key = FACE_TYPES[ct]
                ncorner = 3 if key == "triangle" else 4
                conn = data[:, :ncorner]
                face_block_base[bi] = fid + 1
                face_cells.append((MESHIO_TO_FLAC3D_TYPE[key], conn, fid + 1))
                fid += len(conn)

        zone_groups = cls._resolve_groups(mesh, zone_block_base, ZONE_TYPES)
        face_groups = (
            cls._resolve_groups(mesh, face_block_base, FACE_TYPES)
            if keep_faces else {}
        )
        return cls(points, zone_cells, face_cells, zone_groups, face_groups)

    @staticmethod
    def _resolve_groups(mesh, block_base, type_filter):
        """Turn meshio cell_sets into {name: 1-based global ids} for the given
        cell family (zone or face). Falls back to cell_data gmsh:physical if no
        named cell_sets exist."""
        groups = {}
        cell_sets = getattr(mesh, "cell_sets", None) or {}
        for name, per_block in cell_sets.items():
            if _is_internal_key(name):
                continue
            ids = []
            for bi, local in enumerate(per_block):
                if bi not in block_base or local is None:
                    continue
                local = np.asarray(local)
                if local.size == 0:
                    continue
                ids.append(local + block_base[bi])
            if ids:
                groups[name] = np.unique(np.concatenate(ids))
        if groups:
            return groups
        # Fallback: some readers (e.g. legacy MSH 2.2) put physical groups in
        # cell_data['gmsh:physical'] + field_data instead of cell_sets.
        cell_data = getattr(mesh, "cell_data", None) or {}
        phys = cell_data.get("gmsh:physical")
        field = getattr(mesh, "field_data", None) or {}
        if phys is None or not field:
            return groups
        tag_to_name = {int(v[0]): k for k, v in field.items() if len(v) >= 1}
        acc = {}
        for bi, arr in enumerate(phys):
            if bi not in block_base:
                continue
            arr = np.asarray(arr)
            base = block_base[bi]
            for tag in np.unique(arr):
                name = tag_to_name.get(int(tag))
                if name is None:
                    continue
                local = np.where(arr == tag)[0]
                acc.setdefault(name, []).append(local + base)
        for name, lst in acc.items():
            groups[name] = np.unique(np.concatenate(lst))
        return groups


def _split_slot(name, default_slot):
    """Resolve a group name into (name, slot).

    A physical group named ``"name@slot"`` maps to FLAC3D group ``name`` in
    slot ``slot`` — this lets a zone belong to several groups at once (e.g. a
    well cell that is also part of a reservoir), which FLAC3D supports through
    slots but a single shared slot does not. Names without ``@`` use
    ``default_slot``.
    """
    if "@" in name:
        base, slot = name.rsplit("@", 1)
        base, slot = base.strip(), slot.strip()
        if base and slot:
            return base, slot
    return name, default_slot


def _write_table(f, ids, per_line=10):
    ids = np.asarray(ids, dtype=int)
    for i in range(0, len(ids), per_line):
        f.write("  " + " ".join(str(v) for v in ids[i : i + per_line]) + "\n")


def write_f3grid(grid: Grid, path, float_fmt=".10e", slot="Default"):
    """Write a Grid to a FLAC3D .f3grid ASCII file."""
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"* FLAC3D grid produced by mesh2flac3d {__version__}\n")

        f.write("* GRIDPOINTS\n")
        fmt = "G {:d} " + " ".join(["{:" + float_fmt + "}"] * 3) + "\n"
        for i, (x, y, z) in enumerate(grid.points, start=1):
            f.write(fmt.format(i, x, y, z))

        f.write("* ZONES\n")
        for ftype, conn, base in grid.zone_cells:
            for j, row in enumerate(conn):
                zid = base + j
                nodes = " ".join(str(int(v) + 1) for v in row)
                f.write(f"Z {ftype} {zid} {nodes}\n")

        if grid.zone_groups:
            f.write("* ZONE GROUPS\n")
            for name, ids in grid.zone_groups.items():
                gname, gslot = _split_slot(name, slot)
                f.write(f'ZGROUP "{gname}" SLOT "{gslot}"\n')
                _write_table(f, ids)

        if grid.face_cells:
            f.write("* FACES\n")
            for ftype, conn, base in grid.face_cells:
                for j, row in enumerate(conn):
                    fid = base + j
                    nodes = " ".join(str(int(v) + 1) for v in row)
                    f.write(f"F {ftype} {fid} {nodes}\n")

        if grid.face_groups:
            f.write("* FACE GROUPS\n")
            for name, ids in grid.face_groups.items():
                gname, gslot = _split_slot(name, slot)
                f.write(f'FGROUP "{gname}" SLOT "{gslot}"\n')
                _write_table(f, ids)


def convert(input_path, output_path, keep_faces=True, float_fmt=".10e",
            slot="Default", input_format=None):
    """Read a mesh (any meshio-supported format) and write a FLAC3D .f3grid.

    Parameters
    ----------
    input_path : str
        Source mesh (e.g. Gmsh ``.msh``). Physical volume groups become zone
        groups; physical surface groups become face groups.
    output_path : str
        Destination ``.f3grid``.
    keep_faces : bool
        Export 2D physical groups as FLAC3D faces/FGROUP (for boundary
        conditions). Set False to export zones only.
    float_fmt : str
        Coordinate format spec.
    slot : str
        FLAC3D group slot name.
    input_format : str, optional
        Force a meshio input format instead of inferring from the extension.

    Returns
    -------
    Grid
    """
    import meshio  # imported lazily; meshio is MIT-licensed

    mesh = meshio.read(input_path, file_format=input_format)
    grid = Grid.from_meshio(mesh, keep_faces=keep_faces)
    write_f3grid(grid, output_path, float_fmt=float_fmt, slot=slot)
    return grid
