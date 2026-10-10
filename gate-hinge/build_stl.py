"""Builds gate_hinge_socket.stl with manifold3d, mirroring gate_hinge_socket.scad (default values)."""
import numpy as np, trimesh
from manifold3d import Manifold

bore_d, bore_depth, floor_t, drain_d, chamfer, tip_below_screw = 8.3, 31, 3, 3, 1, 9
offset, wall, sleeve_side = 9, 4, 1  # sleeve_side 1 = left of the screws when facing the wall
plate_t, screw_spacing, slot = 5, 31, 3
screw_d, head_d, head_gap, margin = 4.5, 8.5, 1, 6
FN = 64

boss_d = bore_d + 2 * wall
side_x = sleeve_side * (boss_d / 2 + head_d / 2 + head_gap)  # +X = left when facing the wall
floor_z = -tip_below_screw
boss_top = floor_z + bore_depth
boss_bot = floor_z - floor_t
plate_x0 = min(-head_d / 2 - margin / 2, side_x - boss_d / 2)
plate_x1 = max(head_d / 2 + margin / 2, side_x + boss_d / 2)
plate_top = max(screw_spacing + slot / 2 + margin, boss_top)
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

body = (box(plate_x0, 0, boss_bot, plate_x1 - plate_x0, plate_t, plate_top - boss_bot)
        + cyl(boss_top - boss_bot, boss_d / 2).translate([side_x, offset, boss_bot])
        + box(side_x - boss_d / 2, 0, boss_bot, boss_d, offset, boss_top - boss_bot))
cut = (cyl(bore_depth + 1, bore_d / 2).translate([side_x, offset, floor_z])
       + cyl(chamfer + 0.01, bore_d / 2, bore_d / 2 + chamfer).translate([side_x, offset, boss_top - chamfer])
       + cyl(floor_t + 2, drain_d / 2).translate([side_x, offset, boss_bot - 1])
       + countersunk_hole(0)
       + countersunk_hole(slot).translate([0, 0, screw_spacing]))
part = body - cut

if __name__ == "__main__":
    m = part.to_mesh()
    tm = trimesh.Trimesh(m.vert_properties[:, :3], m.tri_verts)
    tm.export("gate_hinge_socket.stl")
    print("watertight", tm.is_watertight, "volume cm3", round(tm.volume / 1000, 2),
          "bounds", tm.bounds.round(2).tolist(), "sleeve x", round(side_x, 2))
