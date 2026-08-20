// three_layer_box.geo
// Example geometry for mesh2flac3d: a 100 x 100 x 90 box split into three
// horizontal layers, with named physical groups that carry through to FLAC3D.
//
//   Volumes:  Overburden / Salt / Underburden  -> FLAC3D zone groups (ZGROUP)
//   Surfaces: Top / Bottom / Sides             -> FLAC3D face groups  (FGROUP)
//
// Mesh and export:
//   gmsh three_layer_box.geo -3 -o three_layer_box.msh
//   mesh2flac3d three_layer_box.msh out.f3grid

SetFactory("OpenCASCADE");

L = 100;          // horizontal extent (x and y)
t = 30;           // thickness of each layer
eps = 1e-3;       // tolerance for bounding-box selection

// One box per layer, stacked from z = -90 (bottom) up to z = 0 (top).
Box(1) = {0, 0, -90, L, L, t};   // Underburden : z in [-90, -60]
Box(2) = {0, 0, -60, L, L, t};   // Salt        : z in [-60, -30]
Box(3) = {0, 0, -30, L, L, t};   // Overburden  : z in [-30,   0]

// Merge coincident faces so the layers share nodes (conformal mesh).
Coherence;

// --- Volume physical groups (selected by z-range, tag-independent) ---
under()  = Volume In BoundingBox {-eps, -eps, -90-eps,  L+eps, L+eps, -60+eps};
salt()   = Volume In BoundingBox {-eps, -eps, -60-eps,  L+eps, L+eps, -30+eps};
over()   = Volume In BoundingBox {-eps, -eps, -30-eps,  L+eps, L+eps,   0+eps};
Physical Volume("Underburden") = {under()};
Physical Volume("Salt")        = {salt()};
Physical Volume("Overburden")  = {over()};

// --- Surface physical groups (selected by position) ---
top()    = Surface In BoundingBox {-eps, -eps,   0-eps,  L+eps, L+eps,   0+eps};
bottom() = Surface In BoundingBox {-eps, -eps, -90-eps,  L+eps, L+eps, -90+eps};
// four lateral planes: x=0, x=L, y=0, y=L (full height in z)
sx0()    = Surface In BoundingBox {  -eps, -eps, -90-eps,   +eps, L+eps,  0+eps};
sxL()    = Surface In BoundingBox { L-eps, -eps, -90-eps,  L+eps, L+eps,  0+eps};
sy0()    = Surface In BoundingBox {  -eps,  -eps, -90-eps, L+eps,  +eps,  0+eps};
syL()    = Surface In BoundingBox {  -eps, L-eps, -90-eps, L+eps, L+eps,  0+eps};
Physical Surface("Top")    = {top()};
Physical Surface("Bottom") = {bottom()};
Physical Surface("Sides")  = {sx0(), sxL(), sy0(), syL()};

// Mesh size (tune to taste).
Mesh.MeshSizeMax = 25;
