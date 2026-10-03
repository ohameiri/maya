#!/usr/bin/env python3
"""Two-part 3D-printable enclosure (base + lid) for the LR2021 + ESP32-S3 board.

Run with a Python that has CadQuery (python3.11 here): python3.11 gen_enclosure.py

Coordinates are the board STEP frame (kicad-cli pcb export step): X = KiCad X,
Y = -KiCad Y, Z up, board bottom at Z = 0, top at Z = 1.6. Positions below are
written in KiCad (x, y) and converted with ky().

- Split plane at the SMA axis (Z = 2.1): each half carries half of every SMA hole,
  so the board drops in with the connectors fitted.
- Two M2 x 12 screws from below: base standoff -> board hole H1/H2 -> lid pillar.
  A tongue on the base wall locates the lid.
- Openings: USB-C (sized for the plug overmold), SMA threads (the square SMA flange
  bears on the inside of the wall), screw-terminal window (top + front, for wiring),
  GPIO header window, LED holes, two flexure buttons with plungers for RESET/BOOT.

Outputs (next to this script): enclosure_base.stl, enclosure_lid.stl (lid flipped,
ready to print top-down), enclosure_base.step, enclosure_lid.step and
enclosure_assembly.step (parts in assembled position).
"""
import os

import cadquery as cq

HERE = os.path.dirname(os.path.abspath(__file__))


def ky(y):
    """KiCad Y -> STEP Y."""
    return -y


# ---- Board-derived geometry (mm, KiCad coordinates) --------------------------------
BOARD = (100.0, 100.0, 162.0, 147.0)          # x0, y0, x1, y1
HOLES = [(159.2, 118.5), (128.6, 104.0)]      # H1, H2 (M2)
SMA_Y = [105.5, 131.5]                        # J6 2.4 GHz, J5 915 MHz
SMA_Z = 2.1                                   # SMA axis height
USB = dict(y=127.0, z=3.23)                   # J1 opening centre
BUTTONS = [(125.6, 142.2, 'RST'), (131.6, 142.2, 'BOOT')]
BUTTON_TOP = 3.10                             # TS-1187A actuator top (Z)
LEDS = [(147.8, 131.1, 'USR'), (151.6, 131.1, 'PWR')]
TERM_WIN = (99.3, 136.3, 122.1)               # x0, y0, x1 of J2+J3 (to the front wall)
HDR_WIN = (134.9, 140.3, 161.0, 146.3)        # J4 window
SUPPORTS = [(101.6, 101.6), (101.6, 134.5), (156.0, 101.3), (160.8, 137.6)]

# ---- Enclosure parameters ------------------------------------------------------------
INNER = (99.0, 99.5, 163.7, 147.5)            # inner wall faces (x0, y0, x1, y1)
WALL = 2.4
R_OUT = 3.0
Z_BOT = -4.2                                  # base underside
Z_FLOOR = -2.6                                # floor top (THT leads reach -1.9)
Z_SPLIT = SMA_Z
Z_TOP = 12.6                                  # lid top (ceiling 11.0, header top 10.1)
LID_T = 1.6
TONGUE_W, TONGUE_H, FIT = 1.0, 1.2, 0.2


def rect(x0, y0, x1, y1, z0, z1, r=0.0):
    """Box between KiCad (x0,y0)-(x1,y1) and Z z0..z1, optional vertical edge fillet."""
    w, h = x1 - x0, y1 - y0
    b = cq.Workplane('XY').box(w, h, z1 - z0, centered=False).translate((x0, ky(y1), z0))
    if r > 0:
        b = b.edges('|Z').fillet(r)
    return b


def outer(z0, z1):
    x0, y0, x1, y1 = INNER
    return rect(x0 - WALL, y0 - WALL, x1 + WALL, y1 + WALL, z0, z1, R_OUT)


def inner(z0, z1, grow=0.0):
    x0, y0, x1, y1 = INNER
    return rect(x0 - grow, y0 - grow, x1 + grow, y1 + grow, z0, z1, 0.8 + grow)


def cyl_z(x, y, d, z0, z1):
    return cq.Workplane('XY').circle(d / 2).extrude(z1 - z0).translate((x, ky(y), z0))


def openings():
    """Cutters shared by both halves (they straddle the split plane)."""
    c = cq.Workplane('XY')
    # USB-C: room for the plug overmold (13 x 7 mm) through the left wall
    c = c.union(cq.Workplane('YZ').rect(13.4, 7.4).extrude(WALL + 3)
                .edges('|X').fillet(2.4).translate((INNER[0] - WALL - 1.5, ky(USB['y']), USB['z'])))
    # SMA threads (1/4"-36): 6.5 mm holes on the split plane; the 6.35 mm square flange
    # sits against the inside of the wall
    for y in SMA_Y:
        c = c.union(cq.Workplane('YZ').circle(3.25).extrude(WALL + 4)
                    .translate((INNER[2] - 1, ky(y), SMA_Z)))
    # Screw terminals: open top and front (wire entries face the front wall)
    x0, y0, x1 = TERM_WIN
    c = c.union(rect(x0, y0, x1, INNER[3] + WALL + 1, 1.0, Z_TOP + 1))
    return c


def base():
    b = outer(Z_BOT, Z_SPLIT).cut(inner(Z_FLOOR, Z_SPLIT + 1))
    # locating tongue: inner part of the wall, rising above the split plane
    tongue = inner(Z_SPLIT, Z_SPLIT + TONGUE_H, grow=TONGUE_W).cut(inner(Z_SPLIT - 1, Z_SPLIT + TONGUE_H + 1))
    b = b.union(tongue)
    # standoffs under H1/H2 with M2 clearance and a counterbore for the screw head
    for x, y in HOLES:
        b = b.union(cyl_z(x, y, 5.0, Z_FLOOR - 0.1, 0.0))
        b = b.cut(cyl_z(x, y, 2.3, Z_BOT - 1, 0.1))
        b = b.cut(cyl_z(x, y, 4.4, Z_BOT - 1, Z_BOT + 2.0))
    for x, y in SUPPORTS:
        b = b.union(cyl_z(x, y, 3.0, Z_FLOOR - 0.1, 0.0))
    b = b.cut(openings())
    # name on the underside
    b = b.cut(cq.Workplane('XY').workplane(offset=Z_BOT - 0.01)
              .text('LR2021 + ESP32-S3', 4.0, 0.5, combine=False, halign='center', valign='center')
              .mirror('YZ', basePointVector=(0, 0, 0))
              .translate((2 * 131.0, ky(123.5), 0)))
    return b


def lid():
    ceil = Z_TOP - LID_T
    l = outer(Z_SPLIT, Z_TOP).cut(inner(Z_SPLIT - 1, ceil))
    # rebate that takes the base tongue
    l = l.cut(inner(Z_SPLIT - 1, Z_SPLIT + TONGUE_H + FIT, grow=TONGUE_W + FIT))
    # pillars clamping the board at H1/H2, pilot holes for the M2 screws
    for x, y in HOLES:
        l = l.union(cyl_z(x, y, 5.0, 1.6, ceil + 0.1))
        l = l.cut(cyl_z(x, y, 1.7, 1.5, 1.6 + 8.5))
    l = l.cut(openings())
    hx0, hy0, hx1, hy1 = HDR_WIN
    l = l.cut(rect(hx0, hy0, hx1, hy1, ceil - 1, Z_TOP + 1, 0.8))
    for x, y, _ in LEDS:
        l = l.cut(cyl_z(x, y, 2.2, ceil - 1, Z_TOP + 1))
    # flexure buttons: U-slot around a tab hinged at the back, plunger down to the switch
    for x, y, _ in BUTTONS:
        tip, hinge, hw, slot = y + 2.4, y - 6.0, 1.8, 0.5
        u = rect(x - hw - slot, hinge, x + hw + slot, tip + slot, ceil - 1, Z_TOP + 1)
        u = u.cut(rect(x - hw, hinge - 1, x + hw, tip, ceil - 2, Z_TOP + 2))
        l = l.cut(u)
        l = l.cut(rect(x - hw, hinge, x + hw, hinge + 1.5, ceil - 0.1, ceil + 0.8))   # thin hinge
        l = l.union(cyl_z(x, y, 3.0, BUTTON_TOP + 0.3, ceil + 0.1))
    # engraved labels (0.5 mm)
    labels = [(x, y - 7.6, t, 2.2) for x, y, t in BUTTONS]
    labels += [(x, y + 2.7, t, 1.5) for x, y, t in LEDS]
    labels += [(INNER[2] - 4.5, SMA_Y[0], '2.4G', 2.4), (INNER[2] - 4.5, SMA_Y[1], '915', 2.4),
               (INNER[0] + 3.2, USB['y'], 'USB', 2.2), (105.1, 133.6, '5V', 2.4), (116.6, 133.6, '3V3', 2.4),
               (147.6, 137.8, 'GPIO', 2.2), (131.0, 112.0, 'LR2021', 4.0)]
    for x, y, t, s in labels:
        rot = 90 if t == 'USB' else 0
        txt = (cq.Workplane('XY').text(t, s, -0.5, combine=False, halign='center', valign='center')
               .rotate((0, 0, 0), (0, 0, 1), rot).translate((x, ky(y), Z_TOP)))
        l = l.cut(txt)
    return l


def main():
    b, l = base(), lid()
    cq.exporters.export(b, os.path.join(HERE, 'enclosure_base.step'))
    cq.exporters.export(l, os.path.join(HERE, 'enclosure_lid.step'))
    cq.exporters.export(b, os.path.join(HERE, 'enclosure_base.stl'), tolerance=0.02, angularTolerance=0.1)
    # lid printed top-down: flip about X and drop onto Z = 0
    lp = l.rotate((0, 0, 0), (1, 0, 0), 180)
    lp = lp.translate((0, 0, -lp.val().BoundingBox().zmin))
    cq.exporters.export(lp, os.path.join(HERE, 'enclosure_lid.stl'), tolerance=0.02, angularTolerance=0.1)
    asm = cq.Assembly().add(b, name='base', color=cq.Color(0.20, 0.22, 0.25)).add(
        l, name='lid', color=cq.Color(0.85, 0.86, 0.88))
    asm.save(os.path.join(HERE, 'enclosure_assembly.step'))
    # assembled-position meshes for render.py
    os.makedirs(os.path.join(HERE, 'build'), exist_ok=True)
    for name, part in (('base', b), ('lid', l)):
        cq.exporters.export(part, os.path.join(HERE, 'build', f'{name}_assembled.stl'), tolerance=0.02, angularTolerance=0.1)
    for name, part in (('base', b), ('lid', l)):
        bb = part.val().BoundingBox()
        print(f'{name}: {bb.xlen:.1f} x {bb.ylen:.1f} x {bb.zlen:.1f} mm, volume {part.val().Volume() / 1000:.1f} cm3')


if __name__ == '__main__':
    main()
