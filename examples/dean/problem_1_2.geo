// =====================================================================
//  Dean et al. (2006), SPE-79709 - Problems 1 and 2 (shared mesh)
//  "A Comparison of Techniques for Coupling Porous Flow and Geomechanics"
// ---------------------------------------------------------------------
//  Structured hexahedral grid 11 x 11 x 10  (1210 zones, 1584 nodes).
//  Units: SI (metres). z = 0 at the top, z < 0 downwards.
//  Cell size: dx = dy = 200 ft = 60.96 m ; dz = 20 ft = 6.096 m.
//  Domain: X:[0, 670.56]  Y:[0, 670.56]  Z:[-60.96, 0].
//  Well: central column of cells (6th in x and y), all layers.
//
//  The in-plane layout is a 3x3 mosaic (5-1-5 cells wide) so the well
//  (central cell) can be flagged as its own physical group. Each patch
//  is transfinite + recombined, extruded in 10 layers -> hexahedra.
//
//  Physical group names use the "name@slot" convention understood by
//  mesh2flac3d: "well@Well" and "reservoir@Region" land in DIFFERENT
//  FLAC3D slots, so the well cells stay part of the reservoir too.
//
//  Mesh + export:
//    gmsh problem_1_2.geo -3 -o problem_1_2.msh
//    mesh2flac3d problem_1_2.msh problem_1_2.f3grid
// =====================================================================

SetFactory("Built-in");
lc = 50.0;                       // irrelevant: mesh is transfinite

// Cut planes in the XY plane (columns 0 | 5 | 6 | 11)
X[] = {0.0, 304.8, 365.76, 670.56};   // 5*60.96 , +1*60.96 , +5*60.96
Y[] = {0.0, 304.8, 365.76, 670.56};

// Nodes per interval (cells 5,1,5 -> nodes = cells+1)
Nx[] = {6, 2, 6};
Ny[] = {6, 2, 6};
Nz   = 10;                       // layers in z (10 cells)
Hz   = -60.96;                   // total thickness (downwards)

// ---- Points: 4x4 grid at the top (z = 0) ----
For j In {0:3}
  For i In {0:3}
    Point(1 + i + 4*j) = {X[i], Y[j], 0.0, lc};
  EndFor
EndFor

// ---- Horizontal lines (along x): HL = 100 + i + 3*j ----
For j In {0:3}
  For i In {0:2}
    Line(100 + i + 3*j) = {1 + i + 4*j, 1 + (i+1) + 4*j};
  EndFor
EndFor

// ---- In-plane vertical lines (along y): VL = 200 + i + 4*j ----
For j In {0:2}
  For i In {0:3}
    Line(200 + i + 4*j) = {1 + i + 4*j, 1 + i + 4*(j+1)};
  EndFor
EndFor

// ---- Surfaces (9 patches of the 3x3 mosaic): S = 1 + ci + 3*cj ----
For cj In {0:2}
  For ci In {0:2}
    Curve Loop(1 + ci + 3*cj) = {  100 + ci + 3*cj,           // bottom (x)
                                   200 + (ci+1) + 4*cj,        // right (y)
                                 -(100 + ci + 3*(cj+1)),       // top (x)
                                 -(200 + ci + 4*cj) };         // left (y)
    Plane Surface(1 + ci + 3*cj) = {1 + ci + 3*cj};
  EndFor
EndFor

// ---- Transfinite: node count per interval ----
For j In {0:3}
  For ci In {0:2}
    Transfinite Curve{100 + ci + 3*j} = Nx[ci];   // lines along x
  EndFor
EndFor
For cj In {0:2}
  For i In {0:3}
    Transfinite Curve{200 + i + 4*cj} = Ny[cj];   // lines along y
  EndFor
EndFor

For cj In {0:2}
  For ci In {0:2}
    Transfinite Surface{1 + ci + 3*cj};
    Recombine Surface{1 + ci + 3*cj};
  EndFor
EndFor

// ---- Extrude in z (10 layers) -> hexahedra; collect volumes ----
res[] = {};
well  = 0;
For cj In {0:2}
  For ci In {0:2}
    s = 1 + ci + 3*cj;
    out[] = Extrude {0, 0, Hz} { Surface{s}; Layers{Nz}; Recombine; };
    res[] += out[1];                 // out[1] = generated volume
    If (ci == 1 && cj == 1)
      well = out[1];                 // central cell = well
    EndIf
  EndFor
EndFor

// ---- Physical groups (name@slot -> FLAC3D group in that slot) ----
Physical Volume("reservoir@Region") = res[];   // all 1210 zones
Physical Volume("well@Well")        = well;     // central column (well)

// Hexahedra only
Mesh.RecombineAll = 1;
