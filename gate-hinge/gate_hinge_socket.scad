// Stair-gate hinge socket (female part, wall mounted).
// The gate's L-shaped pin drops into the bore; its whole straight leg sits inside the sleeve
// and the pin tip rests on the bore floor, which sets the gate height.
// Axes: X along the wall, Y away from the wall (wall at Y=0), Z up.
// Origin = centre of the lower existing screw hole. The sleeve sits beside the screws so it
// can stay at the original height while both screws remain reachable.
// Print upright (flat bottom on the bed, bore facing up) - no supports needed.

/* [Pin] measured: 7.9 mm wide part, 5 mm neck, ~32 mm straight leg below the bend */
bore_d      = 8.3;   // 7.9 mm pin + clearance
bore_depth  = 31;    // whole straight leg of the pin, stopping just short of the bend
floor_t     = 3;
drain_d     = 3;
chamfer     = 1;     // lead-in at the top of the bore
tip_below_screw = 9;  // pin tip height below the lower screw centre (sets gate height; ~9 on the original part)

/* [Sleeve] */
offset      = 9;     // bore centre distance from the wall (~8.5 on the original part)
wall        = 4;     // sleeve wall thickness around the bore

sleeve_side = 1;     // 1 = sleeve LEFT of the screws when facing the wall, -1 = right

/* [Wall plate - reuses the existing holes] */
plate_t       = 5;
screw_spacing = 31;  // centre to centre of the two existing holes (measure!)
slot          = 3;   // upper hole is a vertical slot so +-1.5 mm spacing error still fits
screw_d       = 4.5;
head_d        = 8.5; // countersink diameter
head_gap      = 1;   // clearance between screw head and sleeve
margin        = 6;   // plate material around the screws

$fn = 64;

boss_d   = bore_d + 2 * wall;
// +X is to the left of someone facing the wall (Y points out of the wall towards them)
side_x   = sleeve_side * (boss_d / 2 + head_d / 2 + head_gap);
floor_z  = -tip_below_screw;
boss_top = floor_z + bore_depth;
boss_bot = floor_z - floor_t;
plate_x0 = min(-head_d / 2 - margin / 2, side_x - boss_d / 2);
plate_x1 = max(head_d / 2 + margin / 2, side_x + boss_d / 2);
plate_top = max(screw_spacing + slot / 2 + margin, boss_top);
cs = (head_d - screw_d) / 2;

module countersunk_hole(len) {
    // a hole along Y, stretched by `len` in Z (len=0 -> round hole)
    hull() for (dz = [-len/2, len/2]) translate([0, -1, dz]) rotate([-90, 0, 0]) cylinder(d = screw_d, h = plate_t + 2);
    hull() for (dz = [-len/2, len/2]) translate([0, plate_t - cs, dz]) rotate([-90, 0, 0])
        cylinder(d1 = screw_d, d2 = head_d, h = cs + 0.01);
}

difference() {
    union() {
        translate([plate_x0, 0, boss_bot]) cube([plate_x1 - plate_x0, plate_t, plate_top - boss_bot]);
        translate([side_x, offset, boss_bot]) cylinder(d = boss_d, h = boss_top - boss_bot);
        translate([side_x - boss_d/2, 0, boss_bot]) cube([boss_d, offset, boss_top - boss_bot]);
    }
    translate([side_x, offset, floor_z]) cylinder(d = bore_d, h = bore_depth + 1);
    translate([side_x, offset, boss_top - chamfer]) cylinder(d1 = bore_d, d2 = bore_d + 2 * chamfer, h = chamfer + 0.01);
    translate([side_x, offset, boss_bot - 1]) cylinder(d = drain_d, h = floor_t + 2);
    countersunk_hole(0);
    translate([0, 0, screw_spacing]) countersunk_hole(slot);
}
