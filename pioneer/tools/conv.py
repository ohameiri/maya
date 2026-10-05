import sys, glob, os
from OCP.STEPControl import STEPControl_Reader
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.StlAPI import StlAPI_Writer
from OCP.Bnd import Bnd_Box
from OCP.BRepBndLib import BRepBndLib
from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_SOLID
src, dst = sys.argv[1], sys.argv[2]
r = STEPControl_Reader(); r.ReadFile(src); r.TransferRoots(); s = r.OneShape()
b = Bnd_Box(); BRepBndLib.Add_s(s, b); m=b.CornerMin(); M=b.CornerMax(); x0,y0,z0,x1,y1,z1 = m.X(),m.Y(),m.Z(),M.X(),M.Y(),M.Z()
d = max(x1-x0,y1-y0,z1-z0)
BRepMesh_IncrementalMesh(s, d/400, False, 0.3, True)
w = StlAPI_Writer(); w.ASCIIMode = False; w.Write(s, dst)
n=0; e=TopExp_Explorer(s, TopAbs_SOLID)
while e.More(): n+=1; e.Next()
print(os.path.basename(src), "bbox", [round(v,1) for v in (x0,y0,z0,x1,y1,z1)], "solids", n)
