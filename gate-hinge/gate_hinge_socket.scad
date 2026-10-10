// Stair-gate hinge socket (female part, wall mounted).
// The gate's L-shaped pin drops vertically into the bore; the pin tip rests on the bore floor.
// Axes: X along the wall, Y away from the wall (wall at Y=0), Z up.
// Print upright (as modelled, plate's bottom edge on the bed) so the arm's layers carry the load.

/* [Pin] */
bore_d      = 9.5;   // pin collar is ~8 mm; 9.5 leaves clearance for easy rotation
bore_depth  = 21;    // how deep the pin goes in
floor_t     = 3;     // material under the pin tip
drain_d     = 3;     // small hole so dust/water falls through

/* [Arm] */
offset      = 18;    // bore centre distance from the wall
boss_d      = 20;    // outer diameter of the round socket
web_w       = 16;    // width of the arm joining boss to plate

/* [Wall plate] */
plate_w     = 26;
plate_h     = 80;
plate_t     = 5;
screw_d     = 4.5;   // for 4 mm wood/plug screws
head_d      = 9;     // countersink diameter
screw_z     = [8, 72];

$fn = 64;

boss_h = bore_depth + floor_t;
boss_z = (plate_h - boss_h) / 2;

difference() {
    union() {
        translate([-plate_w/2, 0, 0]) cube([plate_w, plate_t, plate_h]);
        translate([0, offset, boss_z]) cylinder(d = boss_d, h = boss_h);
        translate([-web_w/2, 0, boss_z]) cube([web_w, offset, boss_h]);
        // 45-degree gusset under the arm
        hull() {
            translate([-4, 0, boss_z - 14]) cube([8, plate_t, 14]);
            translate([-4, 0, boss_z - 1]) cube([8, offset + 4, 1]);
        }
    }
    // bore + lead-in chamfer
    translate([0, offset, boss_z + floor_t]) cylinder(d = bore_d, h = boss_h);
    translate([0, offset, boss_z + boss_h - 2]) cylinder(d1 = bore_d, d2 = bore_d + 4, h = 2.01);
    // drain
    translate([0, offset, -1]) cylinder(d = drain_d, h = plate_h);
    // countersunk screw holes
    for (z = screw_z) {
        translate([0, -1, z]) rotate([-90, 0, 0]) cylinder(d = screw_d, h = plate_t + 2);
        translate([0, plate_t - (head_d - screw_d)/2, z]) rotate([-90, 0, 0])
            cylinder(d1 = screw_d, d2 = head_d, h = (head_d - screw_d)/2 + 0.01);
    }
}
