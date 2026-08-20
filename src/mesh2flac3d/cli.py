"""Command-line interface: ``mesh2flac3d input.msh output.f3grid``."""

from __future__ import annotations

import argparse
import sys

from .core import convert, __version__


def build_parser():
    p = argparse.ArgumentParser(
        prog="mesh2flac3d",
        description="Convert a mesh (Gmsh .msh, VTK, ...) to FLAC3D .f3grid, "
        "preserving physical groups as ZGROUP/FGROUP.",
    )
    p.add_argument("input", help="input mesh (e.g. model.msh)")
    p.add_argument("output", nargs="?", help="output .f3grid (default: input with .f3grid)")
    p.add_argument("--no-faces", action="store_true",
                   help="do not export 2D physical groups as faces/FGROUP")
    p.add_argument("--float-fmt", default=".10e", help="coordinate format (default: .10e)")
    p.add_argument("--slot", default="Default", help="FLAC3D group slot name")
    p.add_argument("--input-format", default=None,
                   help="force meshio input format instead of inferring")
    p.add_argument("--dat", metavar="FILE", default=None,
                   help="also write a FLAC3D command-file skeleton (.dat)")
    p.add_argument("-q", "--quiet", action="store_true", help="suppress summary")
    p.add_argument("--version", action="version", version=f"mesh2flac3d {__version__}")
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    output = args.output
    if output is None:
        output = args.input.rsplit(".", 1)[0] + ".f3grid"

    grid = convert(
        args.input, output,
        keep_faces=not args.no_faces,
        float_fmt=args.float_fmt,
        slot=args.slot,
        input_format=args.input_format,
    )

    if args.dat:
        from .dat import write_dat_skeleton
        write_dat_skeleton(args.dat, output, grid)

    if not args.quiet:
        nz = sum(len(c[1]) for c in grid.zone_cells)
        nf = sum(len(c[1]) for c in grid.face_cells)
        print(f"[mesh2flac3d] {args.input} -> {output}")
        print(f"  points: {len(grid.points)}  zones: {nz}  faces: {nf}")
        if grid.zone_groups:
            print("  zone groups: " + ", ".join(
                f"{k}({len(v)})" for k, v in grid.zone_groups.items()))
        if grid.face_groups:
            print("  face groups: " + ", ".join(
                f"{k}({len(v)})" for k, v in grid.face_groups.items()))
        if args.dat:
            print(f"  command skeleton: {args.dat}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
