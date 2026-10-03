#!/usr/bin/env python3
"""Simplified STEP models for footprints whose model is missing from the KiCad library.

- USB_C_Receptacle_HRO_TYPE-C-31-M-12 (HRO TYPE-C-31-M-12, 8.94 x 7.35 x 3.26 mm)
- SW_Push_1P1T_XKB_TS-1187A (XKB TS-1187A, 5.1 x 5.1 mm, 1.5 mm actuator height)

Coordinates follow KiCad's convention: origin at the footprint origin, model +Y is
footprint -Y (KiCad flips Y), Z up from the board surface. Requires CadQuery.
"""
import os

import cadquery as cq

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'lib', '3d')
METAL = cq.Color(0.82, 0.82, 0.85)
DARK = cq.Color(0.10, 0.10, 0.10)
GOLD = cq.Color(0.85, 0.68, 0.25)
GREY = cq.Color(0.45, 0.45, 0.47)


def stadium(w, h):
    """Rounded-end rectangle in the XZ plane (width along X, height along Z)."""
    return cq.Workplane('XZ').rect(w, h).extrude(1).edges('|Y').fillet(h / 2 - 0.01)


def usb_c_hro():
    W, H, L = 8.94, 3.26, 7.35
    y_front, y_rear = -3.65, 3.65                  # model Y (footprint front is +Y -> model -Y)
    shell = (cq.Workplane('XZ', origin=(0, y_rear, H / 2)).rect(W, H).extrude(L)
             .edges('|Y').fillet(H / 2 - 0.01))
    # cut runs 0.3 mm past the front face so the opening is really open
    cavity = (cq.Workplane('XZ', origin=(0, y_front + 6.2, H / 2)).rect(W - 0.6, H - 0.7).extrude(6.5)
              .edges('|Y').fillet((H - 0.7) / 2 - 0.01))
    shell = shell.cut(cavity)
    tongue = cq.Workplane('XY').box(6.6, 4.5, 0.7).translate((0, y_front + 0.3 + 2.25, H / 2))
    contacts = cq.Workplane('XY')
    for i in range(12):
        x = -2.75 + i * 0.5
        contacts = contacts.union(cq.Workplane('XY').box(0.25, 3.6, 0.76).translate((x, y_front + 0.6 + 1.8, H / 2)))
    # SMD tails on the rear row (footprint y = -4.045 -> model y = +4.045)
    tails = None
    for x, w in ((-3.25, 0.5), (-2.45, 0.5), (2.45, 0.5), (3.25, 0.5)) + tuple(
            (x, 0.25) for x in (-1.75, -1.25, -0.75, -0.25, 0.25, 0.75, 1.25, 1.75)):
        t = cq.Workplane('XY').box(w, 1.1, 0.15).translate((x, 4.0, 0.075))
        tails = t if tails is None else tails.union(t)
    # Through-hole shell pegs (oval slots in the footprint)
    pegs = None
    for x in (-4.32, 4.32):
        for y, hgt in ((3.13, 1.5), (-1.05, 1.0)):
            p = cq.Workplane('XY').box(0.5, hgt, 1.8).translate((x, y, -0.9 + 0.3))
            pegs = p if pegs is None else pegs.union(p)
    asm = cq.Assembly(name='USB_C_Receptacle_HRO_TYPE-C-31-M-12')
    asm.add(shell, name='shell', color=METAL)
    asm.add(pegs, name='pegs', color=METAL)
    asm.add(tails, name='tails', color=METAL)
    asm.add(tongue, name='tongue', color=DARK)
    asm.add(contacts, name='contacts', color=GOLD)
    return asm


def ts1187a():
    body = (cq.Workplane('XY').rect(5.1, 5.1).extrude(1.0)
            .edges('|Z').chamfer(0.4))
    top = cq.Workplane('XY', origin=(0, 0, 1.0)).rect(4.6, 4.6).extrude(0.1)
    actuator = cq.Workplane('XY', origin=(0, 0, 1.1)).circle(1.5).extrude(0.4).faces('>Z').edges().fillet(0.15)
    leads = None
    for sx in (-1, 1):
        for y in (-1.875, 1.875):
            lead = (cq.Workplane('XY').box(0.9, 0.7, 0.2).translate((sx * 3.0, y, 0.1))
                    .union(cq.Workplane('XY').box(0.5, 0.7, 0.6).translate((sx * 2.65, y, 0.3))))
            leads = lead if leads is None else leads.union(lead)
    asm = cq.Assembly(name='SW_Push_1P1T_XKB_TS-1187A')
    asm.add(body, name='body', color=DARK)
    asm.add(top, name='top', color=GREY)
    asm.add(actuator, name='actuator', color=DARK)
    asm.add(leads, name='leads', color=METAL)
    return asm


def main():
    os.makedirs(OUT, exist_ok=True)
    for name, asm in (('USB_C_Receptacle_HRO_TYPE-C-31-M-12', usb_c_hro()),
                      ('SW_Push_1P1T_XKB_TS-1187A', ts1187a())):
        path = os.path.join(OUT, f'{name}.step')
        asm.save(path)
        print('wrote', path)


if __name__ == '__main__':
    main()
