// =====================================================================
//  Dean et al. (2006), SPE-79709 - Problem 3
//  Soft reservoir embedded in stiffer non-pay rock.
// ---------------------------------------------------------------------
//  Variable-spacing structured hexahedral grid 21 x 21 x 12 (5292 zones).
//  Units: SI (metres). z = 0 at the top, z < 0 downwards.
//
//  In-plane block sizes (converted from ft):
//    x: 5 x 4000ft | 5 x 2000ft | 1 x 2000ft | 5 x 2000ft | 5 x 4000ft
//    y: 5 x 2000ft | 5 x 1000ft | 1 x 1000ft | 5 x 1000ft | 5 x 2000ft
//  A 5x5 mosaic isolates the central 11x11 reservoir footprint and the
//  central well cell.
//
//  Vertical layering (top -> bottom), extruded in three stages so the
//  reservoir band is its own set of volumes:
//    overburden : 4000, 3000, 2000, 800, 200 ft   (5 layers)
//    reservoir  : 5 x 50 ft                        (5 layers)
//    underburden: 2 x 100 ft                       (2 layers)
//
//  Physical groups (name@slot convention):
//    reservoir @ Region  -> central 11x11 x 5 reservoir cells (605 zones)
//    well      @ Well     -> central column, reservoir layers   (5 zones)
//
//  Mesh + export:
//    gmsh problem_3.geo -3 -o problem_3.msh
//    mesh2flac3d problem_3.msh problem_3.f3grid
// =====================================================================

SetFactory("Built-in");
lc = 500.0;

// ---- In-plane grid lines (metres) and node counts per interval ----
X[]  = {0.0, 6096.0, 9144.0, 9753.6, 12801.6, 18897.6};
Y[]  = {0.0, 3048.0, 4572.0, 4876.8, 6400.8,  9448.8};
Nx[] = {6, 6, 2, 6, 6};      // cells 5,5,1,5,5  -> nodes 6,6,2,6,6
Ny[] = {6, 6, 2, 6, 6};

// ---- Points: 6x6 grid at the top (z = 0) ----
For j In {0:5}
  For i In {0:5}
    Point(1 + i + 6*j) = {X[i], Y[j], 0.0, lc};
  EndFor
EndFor

// ---- Horizontal lines (along x): 100 + i + 5*j ----
For j In {0:5}
  For i In {0:4}
    Line(100 + i + 5*j) = {1 + i + 6*j, 1 + (i+1) + 6*j};
  EndFor
EndFor

// ---- Vertical lines (along y): 200 + i + 6*j ----
For j In {0:4}
  For i In {0:5}
    Line(200 + i + 6*j) = {1 + i + 6*j, 1 + i + 6*(j+1)};
  EndFor
EndFor

// ---- Surfaces (25 mosaic patches): 1 + ci + 5*cj ----
For cj In {0:4}
  For ci In {0:4}
    Curve Loop(1 + ci + 5*cj) = {  100 + ci + 5*cj,
                                   200 + (ci+1) + 6*cj,
                                 -(100 + ci + 5*(cj+1)),
                                 -(200 + ci + 6*cj) };
    Plane Surface(1 + ci + 5*cj) = {1 + ci + 5*cj};
  EndFor
EndFor

// ---- Transfinite ----
For j In {0:5}
  For ci In {0:4}
    Transfinite Curve{100 + ci + 5*j} = Nx[ci];
  EndFor
EndFor
For cj In {0:4}
  For i In {0:5}
    Transfinite Curve{200 + i + 6*cj} = Ny[cj];
  EndFor
EndFor
For cj In {0:4}
  For ci In {0:4}
    Transfinite Surface{1 + ci + 5*cj};
    Recombine Surface{1 + ci + 5*cj};
  EndFor
EndFor

// ---- Three-stage extrude (heights in metres, downwards) ----
FT = 0.3048;
ZOB  = -10000*FT;   // overburden total thickness
ZRES =   -250*FT;   // reservoir  total thickness (5 x 50 ft)
ZUB  =   -200*FT;   // underburden total thickness (2 x 100 ft)

cur[] = {};
For idx In {0:24}
  cur[idx] = 1 + idx;
EndFor

// stage 1: overburden (5 layers, non-uniform)
nxt[] = {};
For idx In {0:24}
  out[] = Extrude {0,0,ZOB} { Surface{cur[idx]};
          Layers{ {1,1,1,1,1}, {0.4,0.7,0.9,0.98,1.0} }; Recombine; };
  nxt[idx] = out[0];
EndFor
For idx In {0:24}
  cur[idx] = nxt[idx];
EndFor

// stage 2: reservoir (5 equal layers)
nxt[] = {};
For idx In {0:24}
  out[] = Extrude {0,0,ZRES} { Surface{cur[idx]};
          Layers{ {1,1,1,1,1}, {0.2,0.4,0.6,0.8,1.0} }; Recombine; };
  nxt[idx] = out[0];
EndFor
For idx In {0:24}
  cur[idx] = nxt[idx];
EndFor

// stage 3: underburden (2 equal layers)
For idx In {0:24}
  out[] = Extrude {0,0,ZUB} { Surface{cur[idx]};
          Layers{ {1,1}, {0.5,1.0} }; Recombine; };
EndFor

Mesh.RecombineAll = 1;

// ---- Physical groups by geometry ----
// Every volume is tagged in slot "Rock" (three geological bands), so the
// whole grid exports without Mesh.SaveAll (which would drop the tags). The
// soft reservoir (pay) and the well are extra, overlapping groups in their
// own slots -- FLAC3D keeps them all.
eps = 1.0;
Xhi = X[5] + eps;   Yhi = Y[5] + eps;
z0 = 0.0;                    // top
z1 = ZOB;                    // overburden / pay boundary  (~ -3048 m)
z2 = ZOB + ZRES;             // pay / underburden boundary (~ -3124 m)
z3 = ZOB + ZRES + ZUB;       // bottom                     (~ -3185 m)

// Geological bands (slot Rock) -- cover all 5292 zones, non-overlapping.
ob[] = Volume In BoundingBox {-eps, -eps, z1-eps, Xhi, Yhi, z0+eps};
Physical Volume("overburden@Rock")  = {ob[]};
pz[] = Volume In BoundingBox {-eps, -eps, z2-eps, Xhi, Yhi, z1+eps};
Physical Volume("payband@Rock")     = {pz[]};
ub[] = Volume In BoundingBox {-eps, -eps, z3-eps, Xhi, Yhi, z2+eps};
Physical Volume("underburden@Rock") = {ub[]};

// Soft reservoir: central 11x11 footprint within the pay band (slot Region).
res[] = Volume In BoundingBox { X[1]-eps, Y[1]-eps, z2-eps,
                                X[4]+eps, Y[4]+eps, z1+eps };
Physical Volume("reservoir@Region") = {res[]};

// Well: central cell, pay band (slot Well).
wel[] = Volume In BoundingBox { X[2]-eps, Y[2]-eps, z2-eps,
                                X[3]+eps, Y[3]+eps, z1+eps };
Physical Volume("well@Well") = {wel[]};
