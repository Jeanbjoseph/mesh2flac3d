// =====================================================================
//  Dean et al. (2006), SPE-79709 - Problem 4  (quarter five-spot)
// ---------------------------------------------------------------------
//  Water injector in one corner, producer in the diagonally opposite
//  corner. Uniform hexahedral grid 21 x 21 x 11 (4851 zones).
//  Units: SI (metres). z = 0 at the top, z < 0 downwards.
//  Cell size: dx = dy = 60 ft = 18.288 m ; dz = 20 ft = 6.096 m.
//
//  In-plane 3x3 mosaic (1-19-1 cells) isolates the two corner cells so
//  each well is its own group. Extruded one layer at a time so every
//  layer can carry its own permeability group.
//
//  Physical groups (name@slot convention):
//    layer01..layer11 @ Layer  -> per-layer property groups
//    well_inj         @ Well   -> injector corner column (i=0,  j=0)
//    well_prod        @ Well   -> producer corner column (i=20, j=20)
//  A well cell keeps both its layer group and its well group (different
//  slots), which FLAC3D supports.
//
//  Mesh + export:
//    gmsh problem_4.geo -3 -o problem_4.msh
//    mesh2flac3d problem_4.msh problem_4.f3grid
// =====================================================================

SetFactory("Built-in");
lc = 50.0;
FT = 0.3048;
DX = 60*FT;                 // 18.288 m
DZ = 20*FT;                 // 6.096 m
NZ = 11;

// Cut planes: 1 | 19 | 1 cells  -> isolate both corner cells
X[] = {0.0, DX, 20*DX, 21*DX};
Y[] = {0.0, DX, 20*DX, 21*DX};
Nx[] = {2, 20, 2};          // nodes per interval (cells 1,19,1)
Ny[] = {2, 20, 2};

// ---- Points: 4x4 grid at the top (z = 0) ----
For j In {0:3}
  For i In {0:3}
    Point(1 + i + 4*j) = {X[i], Y[j], 0.0, lc};
  EndFor
EndFor

// ---- Horizontal lines (along x) ----
For j In {0:3}
  For i In {0:2}
    Line(100 + i + 3*j) = {1 + i + 4*j, 1 + (i+1) + 4*j};
  EndFor
EndFor

// ---- In-plane vertical lines (along y) ----
For j In {0:2}
  For i In {0:3}
    Line(200 + i + 4*j) = {1 + i + 4*j, 1 + i + 4*(j+1)};
  EndFor
EndFor

// ---- Surfaces (9 mosaic patches) ----
For cj In {0:2}
  For ci In {0:2}
    Curve Loop(1 + ci + 3*cj) = {  100 + ci + 3*cj,
                                   200 + (ci+1) + 4*cj,
                                 -(100 + ci + 3*(cj+1)),
                                 -(200 + ci + 4*cj) };
    Plane Surface(1 + ci + 3*cj) = {1 + ci + 3*cj};
  EndFor
EndFor

// ---- Transfinite ----
For j In {0:3}
  For ci In {0:2}
    Transfinite Curve{100 + ci + 3*j} = Nx[ci];
  EndFor
EndFor
For cj In {0:2}
  For i In {0:3}
    Transfinite Curve{200 + i + 4*cj} = Ny[cj];
  EndFor
EndFor
For cj In {0:2}
  For ci In {0:2}
    Transfinite Surface{1 + ci + 3*cj};
    Recombine Surface{1 + ci + 3*cj};
  EndFor
EndFor

// ---- Extrude one layer at a time (so each layer is its own volume) ----
cur[] = {1, 2, 3, 4, 5, 6, 7, 8, 9};
For k In {0:NZ-1}
  nxt[] = {};
  For idx In {0:8}
    out[] = Extrude {0, 0, -DZ} { Surface{cur[idx]}; Layers{1}; Recombine; };
    nxt[idx] = out[0];              // top surface feeds the next layer
  EndFor
  cur[] = nxt[];
EndFor

Mesh.RecombineAll = 1;

// ---- Physical groups by geometry (bounding-box selection) ----
eps = DX*0.01;
Lx = 21*DX;   Ly = 21*DX;   Lz = NZ*DZ;

// per-layer groups (slot Layer)
For k In {0:NZ-1}
  zlo = -(k+1)*DZ - eps;
  zhi = -k*DZ + eps;
  vlay[] = Volume In BoundingBox {-eps, -eps, zlo, Lx+eps, Ly+eps, zhi};
  Physical Volume(Sprintf("layer%02g@Layer", k+1)) = {vlay[]};
EndFor

// well columns (slot Well), full depth
vinj[]  = Volume In BoundingBox {-eps, -eps, -Lz-eps, DX+eps, DX+eps, eps};
vprod[] = Volume In BoundingBox {20*DX-eps, 20*DX-eps, -Lz-eps, Lx+eps, Ly+eps, eps};
Physical Volume("well_inj@Well")  = {vinj[]};
Physical Volume("well_prod@Well") = {vprod[]};
