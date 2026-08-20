"""Gera uma malha de teste sintetica (sem qualquer dado real): caixa 3 camadas
com grupos fisicos de volume (Overburden/Salt/Underburden) e faces nomeadas
(Top/Bottom/Sides). Usada so para provar o comportamento do meshio e como
fixture de teste. gmsh e usado APENAS aqui (geracao), nunca no produto."""
import gmsh, sys

out = sys.argv[1] if len(sys.argv) > 1 else "box3.msh"
gmsh.initialize()
gmsh.model.add("box3")

L = 100.0
# 3 caixas empilhadas em z
z = [-90, -60, -30, 0]  # underburden, salt, overburden
vols = []
for i in range(3):
    tag = gmsh.model.occ.addBox(0, 0, z[i], L, L, z[i+1]-z[i])
    vols.append(tag)
gmsh.model.occ.synchronize()
# fragmenta pra compartilhar faces (malha conforme)
gmsh.model.occ.fragment([(3, v) for v in vols], [])
gmsh.model.occ.synchronize()

# recuperar volumes por posicao z do centro de massa
vol_ents = gmsh.model.getEntities(3)
def cz(dim, tag):
    return gmsh.model.occ.getCenterOfMass(dim, tag)[2]
vol_sorted = sorted(vol_ents, key=lambda e: cz(*e))
names3 = ["Underburden", "Salt", "Overburden"]
for (dim, tag), nm in zip(vol_sorted, names3):
    pg = gmsh.model.addPhysicalGroup(3, [tag])
    gmsh.model.setPhysicalName(3, pg, nm)

# faces de contorno: top (z=0), bottom (z=-90), laterais
surf = gmsh.model.getEntities(2)
top, bottom, sides = [], [], []
for dim, tag in surf:
    com = gmsh.model.occ.getCenterOfMass(dim, tag)
    zc = com[2]
    nrm = gmsh.model.getNormal(tag, [0.5, 0.5])
    if abs(zc-0.0) < 1e-6:
        top.append(tag)
    elif abs(zc-(-90.0)) < 1e-6:
        bottom.append(tag)
    else:
        # so faces externas laterais (x=0,x=L,y=0,y=L)
        if abs(com[0])<1e-6 or abs(com[0]-L)<1e-6 or abs(com[1])<1e-6 or abs(com[1]-L)<1e-6:
            sides.append(tag)
for tags, nm in [(top,"Top"),(bottom,"Bottom"),(sides,"Sides")]:
    if tags:
        pg = gmsh.model.addPhysicalGroup(2, tags)
        gmsh.model.setPhysicalName(2, pg, nm)

gmsh.option.setNumber("Mesh.MeshSizeMax", 25)
gmsh.model.mesh.generate(3)
gmsh.write(out)
gmsh.finalize()
print("gerado:", out)
