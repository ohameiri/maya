"""Builds gate_hinge_socket.stl with manifold3d, mirroring gate_hinge_socket.scad (default values)."""
import numpy as np, trimesh
from manifold3d import Manifold, Mesh

bore_d, bore_depth, floor_t, drain_d = 9.5, 21, 3, 3
offset, boss_d, web_w = 18, 20, 16
plate_w, plate_h, plate_t = 26, 80, 5
screw_d, head_d, screw_z = 4.5, 9, [8, 72]
FN = 64
boss_h = bore_depth + floor_t
boss_z = (plate_h - boss_h) / 2

def box(x, y, z, sx, sy, sz):
    return Manifold.cube([sx, sy, sz]).translate([x, y, z])

def cyl(h, r1, r2=None):
    return Manifold.cylinder(h, r1, r1 if r2 is None else r2, FN)

def hull(*ms):
    pts = np.vstack([m.to_mesh().vert_properties[:, :3] for m in ms])
    return Manifold.hull_points(pts)

body = (box(-plate_w/2, 0, 0, plate_w, plate_t, plate_h)
        + cyl(boss_h, boss_d/2).translate([0, offset, boss_z])
        + box(-web_w/2, 0, boss_z, web_w, offset, boss_h)
        + hull(box(-4, 0, boss_z - 14, 8, plate_t, 14), box(-4, 0, boss_z - 1, 8, offset + 4, 1)))
cut = (cyl(boss_h, bore_d/2).translate([0, offset, boss_z + floor_t])
       + cyl(2.01, bore_d/2, bore_d/2 + 2).translate([0, offset, boss_z + boss_h - 2])
       + cyl(plate_h, drain_d/2).translate([0, offset, -1]))
cs = (head_d - screw_d) / 2
for z in screw_z:
    cut += cyl(plate_t + 2, screw_d/2).rotate([-90, 0, 0]).translate([0, -1, z])
    cut += cyl(cs + 0.01, screw_d/2, head_d/2).rotate([-90, 0, 0]).translate([0, plate_t - cs, z])
part = body - cut

m = part.to_mesh()
tm = trimesh.Trimesh(m.vert_properties[:, :3], m.tri_verts)
tm.export("gate_hinge_socket.stl")
print("watertight", tm.is_watertight, "volume cm3", round(tm.volume / 1000, 2), "bounds", tm.bounds.tolist())
