"""Builds gate_hinge_socket.stl with manifold3d, mirroring gate_hinge_socket.scad (default values)."""
import numpy as np, trimesh
from manifold3d import Manifold

bore_d, bore_depth, floor_t, drain_d, chamfer = 8.3, 31, 3, 3, 1
offset, wall, top_gap = 12, 4, 6
plate_w, plate_t, screw_spacing, slot = 20, 5, 31, 3
screw_d, head_d, margin_top = 4.5, 8.5, 7
FN = 64

boss_d = bore_d + 2 * wall
boss_top = -top_gap
boss_bot = boss_top - bore_depth - floor_t
plate_top = screw_spacing + slot / 2 + margin_top
cs = (head_d - screw_d) / 2

def box(x, y, z, sx, sy, sz):
    return Manifold.cube([sx, sy, sz]).translate([x, y, z])

def cyl(h, r1, r2=None):
    return Manifold.cylinder(h, r1, r1 if r2 is None else r2, FN)

def hull(*ms):
    return Manifold.hull_points(np.vstack([m.to_mesh().vert_properties[:, :3] for m in ms]))

def countersunk_hole(length):
    dzs = [-length / 2, length / 2]
    shaft = hull(*[cyl(plate_t + 2, screw_d / 2).rotate([-90, 0, 0]).translate([0, -1, dz]) for dz in dzs])
    cone = hull(*[cyl(cs + 0.01, screw_d / 2, head_d / 2).rotate([-90, 0, 0]).translate([0, plate_t - cs, dz]) for dz in dzs])
    return shaft + cone

body = (box(-plate_w / 2, 0, boss_bot, plate_w, plate_t, plate_top - boss_bot)
        + cyl(boss_top - boss_bot, boss_d / 2).translate([0, offset, boss_bot])
        + box(-boss_d / 2, 0, boss_bot, boss_d, offset, boss_top - boss_bot))
cut = (cyl(bore_depth + 1, bore_d / 2).translate([0, offset, boss_top - bore_depth])
       + cyl(chamfer + 0.01, bore_d / 2, bore_d / 2 + chamfer).translate([0, offset, boss_top - chamfer])
       + cyl(floor_t + 2, drain_d / 2).translate([0, offset, boss_bot - 1])
       + countersunk_hole(0)
       + countersunk_hole(slot).translate([0, 0, screw_spacing]))
part = body - cut

m = part.to_mesh()
tm = trimesh.Trimesh(m.vert_properties[:, :3], m.tri_verts)
tm.export("gate_hinge_socket.stl")
print("watertight", tm.is_watertight, "volume cm3", round(tm.volume / 1000, 2), "bounds", tm.bounds.round(2).tolist())
