#!/usr/bin/python3
"""Build the 4-layer PCB from the schematic netlist (KiCad 9 pcbnew API).

Stage 1 (this script): footprints, nets, outline, placement, hand-routed RF
section (50 ohm GCPW, chokes, shunt GND vias), keepouts and copper pours.
Stage 2 (route.py): Freerouting for the remaining nets, then zone fill.

Run with the system python that ships the pcbnew module:  /usr/bin/python3 gen_pcb.py
"""
import math
import os
import re
import subprocess
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from sexpr import S, find, find_all, head, parse  # noqa: E402

PROJ_DIR = os.path.dirname(HERE)
PROJECT = 'lr2021_esp32s3'
PCB = os.path.join(PROJ_DIR, f'{PROJECT}.kicad_pcb')
FPLIB = '/usr/share/kicad/footprints'
LOCAL_MODELS = {'USB_C_Receptacle_HRO_TYPE-C-31-M-12.step', 'SW_Push_1P1T_XKB_TS-1187A.step',
                'ESP32-S3-WROOM-1U.step'}
MM = pcbnew.FromMM

# Board outline (mm). KiCad origin offset keeps the board inside the A4 sheet.
BX0, BY0, BX1, BY1 = 100.0, 100.0, 162.0, 147.0
CORNER_R = 2.0

# LR2021 centre; it is rotated 270 deg so its RF pins (25-32) face the right edge.
UX, UY = 131.0, 118.5
RF_W = 0.38       # 50 ohm GCPW on L1 over the In1 ground (JLC04161H-7628)
PIN_W = 0.25      # width used right at the 0.5 mm-pitch QFN pads
VIA_D, VIA_DR = 0.6, 0.3

# RF row geometry, relative to the LR2021 centre. TX rows at +/-TX_Y, RX rows at +/-RX_Y.
# Series parts sit on the rows at 2.0 mm pitch; shunts are offset 1.5 mm from the row and at
# least 1.46 mm (sum of half courtyards) along the row from any series part.
TX_Y, RX_Y = 6.5, 3.75
TX_RISER_X, RX_RISER_X = 4.5, 5.5
SH = 1.5
X = dict(L_PA=6.0, C_SER=8.0, SH_B=9.5, L_MID=11.0, SH_C=12.5, L_ANT=14.0, SH_ANT=15.5,
         SH_ANT2=16.6, SH_ANT3=17.7, ANT_END=18.6, L_RX=7.0, SH_RX=9.0)


def R(dx, dy):
    """Coordinates relative to the LR2021 centre."""
    return (UX + dx, UY + dy)


def V(p):
    return pcbnew.VECTOR2I(MM(p[0]), MM(p[1]))


# ------------------------------------------------------------------ netlist
def read_netlist():
    out = '/tmp/claude-0/lr2021_netlist.net'
    os.makedirs(os.path.dirname(out), exist_ok=True)
    subprocess.run(['kicad-cli', 'sch', 'export', 'netlist', '--format', 'kicadsexpr', '-o', out,
                    os.path.join(PROJ_DIR, f'{PROJECT}.kicad_sch')], check=True, capture_output=True)
    data = parse(open(out).read())
    comps, nets = {}, {}
    for c in find(data, 'components')[1:]:
        ref = find(c, 'ref')[1]
        fields = {}
        f = find(c, 'fields')
        if f:
            for fld in find_all(f, 'field'):
                if len(fld) > 2:
                    fields[find(fld, 'name')[1]] = fld[2]
        props = {find(p, 'name')[1]: (find(p, 'value') or [None, ''])[1] for p in find_all(c, 'property')}
        comps[ref] = dict(value=find(c, 'value')[1], fp=find(c, 'footprint')[1], uuid=find(c, 'tstamps')[1],
                          fields=fields, dnp='dnp' in props)
    for n in find(data, 'nets')[1:]:
        name = find(n, 'name')[1]
        nets[name] = [(find(nd, 'ref')[1], find(nd, 'pin')[1]) for nd in find_all(n, 'node')]
    return comps, nets


# ------------------------------------------------------------------ placement
# ref: (x, y, rotation). RF parts are placed through place_rf() below so the
# pad carrying a given net ends up on the requested side.
PLACE = {
    # Compact 62 x 46 mm layout. ESP32-S3-WROOM-1U (no PCB antenna, so no keepout) in the
    # top-left corner; the LR2021 RF section and SMAs on the right.
    'U5': (111.4, 110.3, 0),
    'U6': (UX, UY, 270),
    # USB-C on the left edge below the module, opening facing out.
    'J1': (103.0, 127.0, 270),
    'U1': (112.0, 124.6, 0),
    'R1': (110.4, 130.8, 0),
    'R2': (110.4, 132.4, 0),
    # Power path
    'D1': (114.8, 128.0, 0),
    'D2': (114.8, 131.0, 0),
    'D3': (121.5, 132.6, 90),
    'C1': (119.2, 128.4, 90),
    'C2': (121.0, 128.4, 90),
    'U2': (128.0, 133.0, 0),
    'C3': (133.4, 131.1, 90),
    'C4': (135.0, 131.1, 90),
    'C5': (118.9, 132.4, 90),
    'U3': (138.6, 130.5, 0),
    'U4': (138.6, 135.1, 0),
    'C6': (142.4, 130.9, 90),
    'C7': (144.2, 130.9, 90),
    # Screw terminals on the bottom edge. At 0 deg the footprint's wire-entry side (+Y)
    # faces the board edge; body spans Y-5.25 .. Y+4.65.
    'J2': (103.0, 142.0, 0),
    'J3': (114.5, 142.0, 0),
    # ESP32 support: 100 nF right at the 3V3 pin, bulk cap and EN RC below the module
    'C10': (100.95, 103.2, 90),
    'C9': (116.6, 122.0, 0),
    'R4': (119.0, 124.0, 0),
    'C8': (119.0, 125.6, 0),
    'SW1': (125.6, 142.2, 90),
    'SW2': (131.6, 142.2, 90),
    'R5': (121.6, 122.6, 90),
    'R7': (123.0, 122.6, 90),
    'D5': (147.8, 131.1, 0),
    'R6': (147.8, 133.1, 0),
    'D4': (151.6, 131.1, 0),
    'R3': (151.6, 133.1, 0),
    'J4': (136.4, 144.6, 90),
    # LR2021 support: crystal on top (NTC divider left of it), SIMO parts on the left,
    # VBAT decoupling below. Parts whose pad order matters are in _rf_parts().
    'Y1': (*R(-0.6, -6.0), 270),
    'C16': (*R(1.7, -7.4), 90),
    # Two M2 holes on the right edge (the rest of the perimeter is taken by connectors).
    'H1': (BX1 - 2.8, UY, 0),
    'H2': (128.6, 104.0, 0),
}


def _rf_parts():
    t, r, x = TX_Y, RX_Y, X
    parts = []
    for sgn, band in ((-1, 'HF'), (1, 'LF')):
        out = 'down' if sgn < 0 else None   # pad on the row faces the row
        inn = None if sgn < 0 else 'down'   # pad facing the chip side
        ty, ry = sgn * t, sgn * r
        if band == 'HF':
            parts += [
                ('L8', 'v', R(TX_RISER_X, ty - SH), '/VR_PA', inn),
                ('C26', 'v', R(TX_RISER_X, ty - 2 * SH - 0.5 + 0.0), '/VR_PA', out),
                ('L9', 'h', R(x['L_PA'], ty), '/RFO_HF'),
                ('C27', 'h', R(x['C_SER'], ty), '/HF_A'),
                ('C28', 'v', R(x['SH_B'], ty - SH), '/HF_B', out),
                ('L10', 'h', R(x['L_MID'], ty), '/HF_B'),
                ('C29', 'h', R(x['L_MID'], ty + 1.2), '/HF_B'),
                ('C30', 'v', R(x['SH_C'], ty - SH), '/HF_C', out),
                ('C32', 'v', R(x['SH_C'], ty + SH), '/HF_C'),
                ('L11', 'h', R(x['L_ANT'], ty), '/HF_C'),
                ('C31', 'v', R(x['SH_ANT'], ty - SH), '/ANT_HF', out),
                ('L12', 'v', R(x['SH_ANT'], ty + SH), '/ANT_HF'),
                ('D7', 'v', R(x['SH_ANT2'], ty - SH), '/ANT_HF', out),
                ('L13', 'h', R(x['L_RX'], ry), '/RFI_HF'),
                ('C33', 'v', R(x['SH_RX'], ry + SH), '/HF_RX'),
            ]
        else:
            parts += [
                ('L2', 'v', R(TX_RISER_X, ty + SH), '/RFO_LF'),
                ('C18', 'v', R(TX_RISER_X, ty + 2 * SH + 0.5), '/VR_PA'),
                ('L3', 'h', R(x['L_PA'], ty), '/RFO_LF'),
                ('C19', 'h', R(x['C_SER'], ty), '/LF_A'),
                ('C20', 'v', R(x['SH_B'], ty + SH), '/LF_B'),
                ('L4', 'h', R(x['L_MID'], ty), '/LF_B'),
                ('C21', 'h', R(x['L_MID'], ty - 1.2), '/LF_B'),
                ('C22', 'v', R(x['SH_C'], ty + SH), '/LF_C'),
                ('L5', 'h', R(x['L_ANT'], ty), '/LF_C'),
                ('C23', 'v', R(x['SH_ANT'], ty + SH), '/ANT_LF'),
                ('L6', 'v', R(x['SH_ANT2'], ty + SH), '/ANT_LF'),
                ('D6', 'v', R(x['SH_ANT3'], ty + SH), '/ANT_LF'),
                ('C24', 'v', R(x['SH_ANT'], ty - SH), '/LF_RX'),
                ('L7', 'h', R(x['L_RX'], ry), '/RFI_LF'),
                ('C25', 'v', R(x['SH_RX'], ry - SH), '/LF_RX', 'down'),
            ]
    parts += [
        ('C17', 'v', R(2.6, -4.6), '/VR_PA', 'down'),
        ('C14', 'v', R(3.3, 4.6), '/VDCC'),
        # NTC divider next to the crystal
        ('R8', 'v', R(-3.2, -4.6), '/LR_VNTC', 'down'),
        ('TH1', 'v', R(-3.2, -6.6), '/LR_NTC', 'down'),
        # SIMO outputs: VDCC1 caps above the VPAX1 trace, VPAX1 caps below it
        ('C13', 'v', R(-4.2, -1.25), '/VDCC1', 'down'),
        ('FB2', 'v', R(-5.5, -1.25), '/VDCC1', 'down'),
        ('C15', 'v', R(-6.8, 1.25), '/VPAX1'),
        ('FB3', 'v', R(-8.1, 1.25), '/VPAX1'),
        ('L1', 'h', R(-4.8, 2.4), '/LXB'),
        # VBAT decoupling and feed
        ('C11', 'v', R(-1.75, 4.3), '/LR_VBAT'),
        ('C12', 'v', R(-3.0, 4.3), '/LR_VBAT'),
        ('FB1', 'v', R(-4.5, 4.3), '/LR_VBAT'),
    ]
    return parts


RF_PARTS = _rf_parts()
SMA_HF = (BX1 - 2.1, UY - 13.0)
SMA_LF = (BX1 - 2.1, UY + 13.0)
VR_PA_IN2_X = 3.95



# ------------------------------------------------------------------ via placement helper
class ViaPlacer:
    """Finds free spots for plane/stitching vias. Works on axis-aligned pad and
    courtyard boxes, so it is conservative."""
    CLR = 0.22      # copper clearance used for the check (rules: 0.15-0.2)
    HOLE_GAP = 0.3  # hole-to-hole

    def __init__(self, board):
        T = pcbnew.ToMM
        self.board = board
        self.pads, self.segs, self.vias, self.courts, self.keepouts = [], [], [], [], []
        for fp in board.GetFootprints():
            for pad in fp.Pads():
                bb = pad.GetBoundingBox()
                self.pads.append((pad.GetNetname(), (T(bb.GetLeft()), T(bb.GetTop()), T(bb.GetRight()), T(bb.GetBottom())),
                                  pad.IsOnLayer(pcbnew.F_Cu), pad.IsOnLayer(pcbnew.B_Cu), fp.GetReference(),
                                  pad.GetAttribute() in (pcbnew.PAD_ATTRIB_PTH, pcbnew.PAD_ATTRIB_NPTH)))
            cy = fp.GetCourtyard(pcbnew.F_CrtYd)
            if cy.OutlineCount():
                bb = cy.BBox()
                self.courts.append((fp.GetReference(), (T(bb.GetLeft()), T(bb.GetTop()), T(bb.GetRight()), T(bb.GetBottom())),
                                    pcbnew.SHAPE_POLY_SET(cy)))
            for z in fp.Zones():
                if z.GetIsRuleArea() and z.GetDoNotAllowVias():
                    bb = z.GetBoundingBox()
                    self.keepouts.append((T(bb.GetLeft()), T(bb.GetTop()), T(bb.GetRight()), T(bb.GetBottom())))
        for t in board.GetTracks():
            if t.GetClass() == 'PCB_VIA':
                p = t.GetPosition()
                self.vias.append((t.GetNetname(), (T(p.x), T(p.y)), T(t.GetWidth(pcbnew.F_Cu)) / 2))
            else:
                self.segs.append((t.GetNetname(), (T(t.GetStart().x), T(t.GetStart().y)),
                                  (T(t.GetEnd().x), T(t.GetEnd().y)), T(t.GetWidth()) / 2, t.GetLayer()))

    @staticmethod
    def _box_dist(p, b):
        dx = max(b[0] - p[0], 0, p[0] - b[2])
        dy = max(b[1] - p[1], 0, p[1] - b[3])
        return math.hypot(dx, dy)

    @staticmethod
    def _seg_dist(p, a, b):
        ax, ay = b[0] - a[0], b[1] - a[1]
        L = ax * ax + ay * ay
        t = 0 if L == 0 else max(0, min(1, ((p[0] - a[0]) * ax + (p[1] - a[1]) * ay) / L))
        return math.hypot(p[0] - a[0] - t * ax, p[1] - a[1] - t * ay)

    def via_ok(self, net, p, r, own_ref=None, margin=0.6):
        if not (BX0 + margin <= p[0] <= BX1 - margin and BY0 + margin <= p[1] <= BY1 - margin):
            return False
        for k in self.keepouts:
            if self._box_dist(p, k) < r + 0.1:
                return False
        for ref, b, poly in self.courts:
            if ref == own_ref or self._box_dist(p, b) > r:
                continue
            # inside (or within r/2 of) the real courtyard outline
            if poly.Contains(V(p)) or any(poly.Contains(V((p[0] + ex, p[1] + ey)))
                                          for ex, ey in ((r / 2, 0), (-r / 2, 0), (0, r / 2), (0, -r / 2))):
                return False
        for pnet, b, *_rest in self.pads:
            if pnet != net and self._box_dist(p, b) < r + self.CLR:
                return False
            if _rest[3] and self._box_dist(p, b) < r + self.HOLE_GAP:   # through-hole pads
                return False
        for vnet, c, vr in self.vias:
            d = math.hypot(p[0] - c[0], p[1] - c[1])
            if d < r + vr + (self.HOLE_GAP if vnet == net else self.CLR):
                return False
        for snet, a, b, hw, _layer in self.segs:
            if snet != net and self._seg_dist(p, a, b) < r + hw + self.CLR:
                return False
        return True

    def stub_ok(self, net, a, b, hw, layer_front=True):
        for pnet, bb, on_f, on_b, *_ in self.pads:
            if pnet == net or not (on_f if layer_front else on_b):
                continue
            # sample the segment
            for i in range(11):
                q = (a[0] + (b[0] - a[0]) * i / 10, a[1] + (b[1] - a[1]) * i / 10)
                if self._box_dist(q, bb) < hw + self.CLR:
                    return False
        for snet, s0, s1, shw, layer in self.segs:
            if snet == net or layer != (pcbnew.F_Cu if layer_front else pcbnew.B_Cu):
                continue
            for i in range(11):
                q = (a[0] + (b[0] - a[0]) * i / 10, a[1] + (b[1] - a[1]) * i / 10)
                if self._seg_dist(q, s0, s1) < hw + shw + self.CLR:
                    return False
        return True

    def pads_near(self, p, d):
        return any(self._box_dist(p, b) < d for _n, b, *_ in self.pads)

    def add(self, net, p, r):
        self.vias.append((net, p, r))

    def add_seg(self, net, a, b, hw, layer=pcbnew.F_Cu):
        self.segs.append((net, a, b, hw, layer))


class Builder:
    def __init__(self):
        self.comps, self.nets = read_netlist()
        if os.path.exists(PCB):
            os.remove(PCB)
        self.board = pcbnew.NewBoard(PCB)
        self.board.SetCopperLayerCount(4)
        self.netinfo = {}
        self.fps = {}

    # -------------------------------------------------------------- basics
    def net(self, name):
        return self.netinfo[name]

    def add_nets(self):
        for name in self.nets:
            n = pcbnew.NETINFO_ITEM(self.board, name)
            self.board.Add(n)
            self.netinfo[name] = n

    def add_footprints(self):
        pinnet = {}
        for name, nodes in self.nets.items():
            for ref, pin in nodes:
                pinnet[(ref, pin)] = name
        for ref, c in sorted(self.comps.items()):
            lib, fpname = c['fp'].split(':')
            fp = pcbnew.FootprintLoad(f'{FPLIB}/{lib}.pretty', fpname)
            if fp is None:
                raise SystemExit(f'footprint {c["fp"]} not found for {ref}')
            fp.SetFPIDAsString(c['fp'])
            fp.SetReference(ref)
            fp.SetValue(c['value'])
            fp.SetPath(pcbnew.KIID_PATH('/' + c['uuid']))
            fp.SetSheetfile(f'{PROJECT}.kicad_sch')
            fp.SetSheetname('')
            for k, v in c['fields'].items():
                if k not in ('Footprint', 'Datasheet', 'Description') and v:
                    fp.SetField(k, v)
                    fld = fp.GetFieldByName(k)
                    if fld:
                        fld.SetVisible(False)
            if c['dnp']:
                fp.SetDNP(True)
            for pad in fp.Pads():
                n = pinnet.get((ref, pad.GetNumber()))
                if n:
                    pad.SetNet(self.net(n))
            self.board.Add(fp)
            self.fps[ref] = fp

    def place(self, ref, x, y, rot):
        fp = self.fps[ref]
        fp.SetPosition(V((x, y)))
        fp.SetOrientationDegrees(rot)

    def pad_net(self, ref, padnum):
        p = self.fps[ref].FindPadByNumber(padnum)
        return p.GetNetname() if p else None

    def place_rf(self, ref, axis, c, net, side=None):
        """Rotate a 2-pad part so the pad on `net` faces left ('h') or up ('v')."""
        first_is_pad1 = self.pad_net(ref, '1') == net
        if axis == 'h':
            rot = 0 if first_is_pad1 else 180
        else:
            rot = 270 if first_is_pad1 else 90  # 270 puts pad 1 on top
        if side == 'down':  # requested pad faces down instead
            rot = (rot + 180) % 360
        self.place(ref, c[0], c[1], rot)

    def padpos(self, ref, net):
        hits = [p for p in self.fps[ref].Pads() if p.GetNetname() == net]
        if not hits:
            raise SystemExit(f'{ref} has no pad on {net}')
        p = hits[0].GetPosition()
        return (pcbnew.ToMM(p.x), pcbnew.ToMM(p.y))

    def track(self, net, pts, w=RF_W, layer=pcbnew.F_Cu, lock=True):
        for a, b in zip(pts, pts[1:]):
            if abs(a[0] - b[0]) < 1e-6 and abs(a[1] - b[1]) < 1e-6:
                continue
            t = pcbnew.PCB_TRACK(self.board)
            t.SetStart(V(a))
            t.SetEnd(V(b))
            t.SetWidth(MM(w))
            t.SetLayer(layer)
            t.SetNet(self.net(net))
            t.SetLocked(lock)
            self.board.Add(t)

    def via(self, net, p, d=VIA_D, dr=VIA_DR, lock=True):
        v = pcbnew.PCB_VIA(self.board)
        v.SetPosition(V(p))
        v.SetWidth(MM(d))
        v.SetDrill(MM(dr))
        v.SetNet(self.net(net))
        v.SetLocked(lock)
        self.board.Add(v)

    def gnd_via_for(self, ref, at):
        """Short track from the part's GND pad to a stitching via at `at`."""
        self.track('GND', [self.padpos(ref, 'GND'), at], w=0.4)
        self.via('GND', at)

    # -------------------------------------------------------------- outline
    def outline(self):
        x0, y0, x1, y1, r = BX0, BY0, BX1, BY1, CORNER_R

        def seg(a, b):
            s = pcbnew.PCB_SHAPE(self.board)
            s.SetShape(pcbnew.SHAPE_T_SEGMENT)
            s.SetStart(V(a))
            s.SetEnd(V(b))
            s.SetLayer(pcbnew.Edge_Cuts)
            s.SetWidth(MM(0.05))
            self.board.Add(s)

        def arc(c, start, angle):
            s = pcbnew.PCB_SHAPE(self.board)
            s.SetShape(pcbnew.SHAPE_T_ARC)
            s.SetCenter(V(c))
            s.SetStart(V(start))
            s.SetArcAngleAndEnd(pcbnew.EDA_ANGLE(angle, pcbnew.DEGREES_T))
            s.SetLayer(pcbnew.Edge_Cuts)
            s.SetWidth(MM(0.05))
            self.board.Add(s)

        seg((x0 + r, y0), (x1 - r, y0))
        seg((x1, y0 + r), (x1, y1 - r))
        seg((x1 - r, y1), (x0 + r, y1))
        seg((x0, y1 - r), (x0, y0 + r))
        arc((x1 - r, y0 + r), (x1 - r, y0), 90)
        arc((x1 - r, y1 - r), (x1, y1 - r), 90)
        arc((x0 + r, y1 - r), (x0 + r, y1), 90)
        arc((x0 + r, y0 + r), (x0, y0 + r), 90)

    # -------------------------------------------------------------- zones
    def zone(self, net, layer, pts, priority=0, clearance=0.2, name=None, rule_area=False, keepout=None):
        z = pcbnew.ZONE(self.board)
        if rule_area:
            z.SetIsRuleArea(True)
            ls = pcbnew.LSET()
            for l in layer:
                ls.AddLayer(l)
            z.SetLayerSet(ls)
            ko = keepout or {}
            z.SetDoNotAllowTracks(ko.get('tracks', True))
            z.SetDoNotAllowVias(ko.get('vias', True))
            z.SetDoNotAllowPads(ko.get('pads', False))
            z.SetDoNotAllowCopperPour(ko.get('pour', False))
            z.SetDoNotAllowFootprints(ko.get('footprints', False))
        else:
            z.SetLayer(layer)
            z.SetNet(self.net(net))
            z.SetAssignedPriority(priority)
            z.SetLocalClearance(MM(clearance))
            z.SetMinThickness(MM(0.2))
            z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
            z.SetThermalReliefGap(MM(0.25))
            z.SetThermalReliefSpokeWidth(MM(0.3))
            z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
        if name:
            z.SetZoneName(name)
        poly = pcbnew.VECTOR_VECTOR2I()
        for p in pts:
            poly.append(V(p))
        z.AddPolygon(poly)
        self.board.Add(z)
        return z

    def ground_pours(self):
        m = 0.3
        rect = [(BX0 + m, BY0 + m), (BX1 - m, BY0 + m), (BX1 - m, BY1 - m), (BX0 + m, BY1 - m)]
        self.zone('GND', pcbnew.In1_Cu, rect, priority=0, clearance=0.2, name='GND_PLANE')
        self.zone('+3V3', pcbnew.In2_Cu, rect, priority=0, clearance=0.2, name='3V3_PLANE')
        for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
            self.zone('GND', layer, rect, priority=0, clearance=0.2, name=f'GND_{layer}')

    # -------------------------------------------------------------- RF routing
    def route_rf(self):
        pp = self.padpos
        U = self.fps['U6']

        def pin(n):
            p = U.FindPadByNumber(str(n)).GetPosition()
            return (pcbnew.ToMM(p.x), pcbnew.ToMM(p.y))

        def row_drop(net, ref, row_y):
            """Stub from the row (at the part's x) to the part's pad on `net`."""
            p = pp(ref, net)
            self.track(net, [(p[0], UY + row_y), p])

        def band(sgn, b, pa_pins, rx_pin, rx_tap_ref, rx_tap_net):
            ty, ry = sgn * TX_Y, sgn * RX_Y
            rfo, rfi = f'/RFO_{b}', f'/RFI_{b}'
            a, bb, c, ant, rx = f'/{b}_A', f'/{b}_B', f'/{b}_C', f'/ANT_{b}', f'/{b}_RX'
            refs = dict(HF=dict(lpa='L9', cser='C27', shb='C28', lmid='L10', par='C29', shc='C30', lant='L11',
                                lrx='L13', shrx='C33', ant=('C31', 'L12', 'D7'), choke='L8'),
                        LF=dict(lpa='L3', cser='C19', shb='C20', lmid='L4', par='C21', shc='C22', lant='L5',
                                lrx='L7', shrx='C25', ant=('C23', 'L6', 'D6', 'C24'), choke='L2'))[b]
            # TX: PA pin(s) -> riser -> row
            if len(pa_pins) == 2:
                p0, p1 = pin(pa_pins[0]), pin(pa_pins[1])
                jx = UX + 3.2
                self.track(rfo, [p0, (jx, p0[1]), (jx, p1[1]), p1], w=PIN_W)
                mid = (jx, (p0[1] + p1[1]) / 2)
                self.track(rfo, [mid, (UX + TX_RISER_X, mid[1])], w=PIN_W)
                start = (UX + TX_RISER_X, mid[1])
            else:
                p0 = pin(pa_pins[0])
                self.track(rfo, [p0, (UX + TX_RISER_X, p0[1])], w=PIN_W)
                start = (UX + TX_RISER_X, p0[1])
            neck = (start[0], start[1] + sgn * 0.55)
            self.track(rfo, [start, neck], w=PIN_W)
            node = R(TX_RISER_X, ty)
            self.track(rfo, [neck, node, pp(refs['lpa'], rfo)])
            self.track(rfo, [node, pp(refs['choke'], rfo)])
            self.track(a, [pp(refs['lpa'], a), pp(refs['cser'], a)])
            self.track(bb, [pp(refs['cser'], bb), pp(refs['lmid'], bb)])
            row_drop(bb, refs['shb'], ty)
            self.track(bb, [pp(refs['lmid'], bb), pp(refs['par'], bb)])
            self.track(c, [pp(refs['lmid'], c), pp(refs['lant'], c)])
            self.track(c, [pp(refs['lmid'], c), pp(refs['par'], c)])
            row_drop(c, refs['shc'], ty)
            end = R(X['ANT_END'], ty)
            self.track(ant, [pp(refs['lant'], ant), end])
            for ref in refs['ant']:
                row_drop(ant, ref, ty)
            # RX: pin -> riser -> row -> tap
            q = pin(rx_pin)
            self.track(rfi, [q, (UX + RX_RISER_X, q[1]), (UX + RX_RISER_X, q[1] + sgn * 0.6)], w=PIN_W)
            self.track(rfi, [(UX + RX_RISER_X, q[1] + sgn * 0.6), R(RX_RISER_X, ry), pp(refs['lrx'], rfi)])
            tap = pp(rx_tap_ref, rx)
            self.track(rx, [pp(refs['lrx'], rx), (tap[0], UY + ry), tap])
            row_drop(rx, refs['shrx'], ry)
            if b == 'HF':
                row_drop(c, rx_tap_ref, ty)
            return end

        ant_hf_end = band(-1, 'HF', [32], 31, 'C32', '/HF_RX')
        ant_lf_end = band(1, 'LF', [28, 27], 29, 'C24', '/LF_RX')

        # Antenna feeds: straight, one 45 deg bend, 4 mm straight into the SMA pin.
        feeds = []
        for end, ref, net in ((ant_hf_end, 'J6', '/ANT_HF'), (ant_lf_end, 'J5', '/ANT_LF')):
            j = pp(ref, net)
            xd = j[0] - 3.0 - abs(j[1] - end[1])
            self.track(net, [end, (xd, end[1]), (j[0] - 3.0, j[1]), j])
            feeds.append((end, xd, j))

        # ---- VR_PA: pin 1 -> C17 -> HF choke L8/C26; In2 link to the LF choke L2/C18
        l8, c26 = pp('L8', '/VR_PA'), pp('C26', '/VR_PA')
        self.track('/VR_PA', [pin(1), R(1.75, -3.5)], w=PIN_W)
        self.track('/VR_PA', [R(1.75, -3.5), R(3.4, -3.5), (UX + 3.4, l8[1]), l8], w=0.3)
        self.track('/VR_PA', [R(2.6, -3.5), pp('C17', '/VR_PA')], w=0.3)
        self.track('/VR_PA', [l8, c26], w=0.3)
        top_via = (UX + 3.4, c26[1])
        self.track('/VR_PA', [(UX + 3.4, l8[1]), top_via], w=0.3)
        self.via('/VR_PA', top_via)
        l2, c18 = pp('L2', '/VR_PA'), pp('C18', '/VR_PA')
        bot_via = (UX + 3.4, c18[1])
        self.via('/VR_PA', bot_via)
        xi = UX + VR_PA_IN2_X
        self.track('/VR_PA', [top_via, (xi, top_via[1] + 0.55), (xi, bot_via[1] - 0.55), bot_via],
                   w=0.4, layer=pcbnew.B_Cu)
        self.track('/VR_PA', [bot_via, (UX + 3.4, l2[1]), l2], w=0.3)
        self.track('/VR_PA', [l2, c18], w=0.3)

        # ---- GND for shunt parts: short stub to a stitching via (offset from the GND pad)
        for ref, d in (('C26', (0, -1.0)), ('C28', (0, -1.0)), ('C30', (0, -1.0)), ('C31', (0, -1.0)),
                       ('D7', (0, -1.0)), ('L12', (0, 0.95)), ('C33', (0, 0.85)), ('C17', (-0.7, 0)),
                       ('C18', (0, 1.0)), ('C20', (0, 1.0)), ('C22', (0, 1.0)), ('C23', (0, 1.0)),
                       ('L6', (0, 1.0)), ('D6', (0, 1.0)), ('C25', (0, -0.85)), ('C14', (-0.6, 0.9))):
            g = self.padpos(ref, 'GND')
            self.gnd_via_for(ref, (g[0] + d[0], g[1] + d[1]))
        # QFN ground pins straight into the exposed pad
        for n in (30, 15):
            p = pin(n)
            self.track('GND', [p, (UX + (p[0] - UX) * 0.6, p[1])], w=PIN_W)
        # VDCC2 escape between the chip and the LF riser
        self.track('/VDCC', [pin(26), R(3.3, 1.25), pp('C14', '/VDCC')], w=PIN_W)
        self.fanout_lr2021(pin)

        # Stitching vias along both sides of the antenna feeds and around the SMA launch
        for end, xd, j in feeds:
            x = end[0] + 1.0
            while x < xd - 0.3:
                for s in (-1.0, 1.0):
                    self.via('GND', (x, end[1] + s))
                x += 1.6
            for dx in (-2.0, -1.0):
                for s in (-1.3, 1.3):
                    self.via('GND', (j[0] + dx, j[1] + s))
        self.rf_feeds = feeds


    def fanout_lr2021(self, pin):
        """Escape every remaining LR2021 pin to a part pad or a via (QFN pitch is too tight
        for the autorouter to do this reliably)."""
        pp = self.padpos
        SV = (0.5, 0.25)  # signal fanout via

        def sig(net, pts, via=True, w=0.2):
            self.track(net, pts, w=w)
            if via:
                self.via(net, pts[-1], *SV)

        def gnd(ref, at, pad=None):
            g = pad or pp(ref, 'GND')
            self.track('GND', [g, at], w=0.3)
            self.via('GND', at)

        # Top row: XTA straight up, XTB around the left of the crystal, VTCXO -> R8,
        # NTC over the top of the crystal to the divider, VPAX2 -> C16.
        self.track('/XTA', [pin(4), R(0.25, -4.6), pp('Y1', '/XTA')], w=0.2)
        self.track('/XTB', [pin(5), R(-0.25, -3.95), R(-2.0, -3.95), R(-2.0, -6.7), pp('Y1', '/XTB')], w=0.2)
        y1 = self.fps['Y1']
        for padnum, at in (('2', R(-1.15, -4.65)), ('4', R(-0.05, -7.55))):
            p = y1.FindPadByNumber(padnum).GetPosition()
            gnd('Y1', at, (pcbnew.ToMM(p.x), pcbnew.ToMM(p.y)))
        self.track('/LR_VNTC', [pin(6), R(-0.75, -3.55), R(-3.2, -3.55), pp('R8', '/LR_VNTC')], w=0.2)
        self.track('/LR_NTC', [pp('R8', '/LR_NTC'), pp('TH1', '/LR_NTC')], w=0.2)
        self.track('/LR_NTC', [pin(3), R(0.75, -8.3), R(-2.6, -8.3), R(-2.6, -6.12), pp('TH1', '/LR_NTC')], w=0.2)
        gnd('TH1', R(-4.1, -7.08))
        self.track('/VPAX', [pin(2), R(1.25, -5.6), R(1.7, -6.05), pp('C16', '/VPAX')], w=0.25)
        self.track('/VPAX', [R(1.7, -6.3), R(2.25, -6.3)], w=0.25)
        self.via('/VPAX', R(2.25, -6.3), *SV)
        gnd('C16', R(1.7, -8.75))
        # Left column: DIO9 to a via, VDCC1 / VPAX1 straight out to their caps and
        # ferrites, LXA/LXB down to the SIMO inductor, GND_DCC into the exposed pad.
        sig('/LR_DIO9', [pin(9), R(-2.9, -1.75), R(-3.3, -2.15), R(-3.3, -2.3)])
        self.track('/VDCC1', [pin(12), R(-5.5, -0.25)], w=0.25)
        for ref in ('C13', 'FB2'):
            p = pp(ref, '/VDCC1')
            self.track('/VDCC1', [(p[0], UY - 0.25), p], w=0.25)
        gnd('C13', R(-4.2, -2.55))
        p = pp('FB2', '/VDCC')
        self.track('/VDCC', [p, R(-5.5, -2.55)], w=0.25)
        self.via('/VDCC', R(-5.5, -2.55), *SV)
        self.via('/VDCC', R(3.3, 2.3), *SV)
        # VDCC2 (right side) back to FB2 on the left: on B.Cu, between the exposed-pad
        # thermal vias and the bottom-row fanout vias, then up the left side.
        self.track('/VDCC', [R(3.3, 2.3), R(-2.9, 2.3), R(-2.9, -1.6), R(-5.5, -1.6), R(-5.5, -2.55)],
                   w=0.25, layer=pcbnew.B_Cu)
        self.track('/VPAX1', [pin(13), R(-8.1, 0.25)], w=0.25)
        for ref in ('C15', 'FB3'):
            p = pp(ref, '/VPAX1')
            self.track('/VPAX1', [(p[0], UY + 0.25), p], w=0.25)
        gnd('C15', R(-6.8, 2.6))
        p = pp('FB3', '/VPAX')
        self.track('/VPAX', [p, R(-8.1, 2.6)], w=0.25)
        self.via('/VPAX', R(-8.1, 2.6), *SV)
        lxb, lxa = pp('L1', '/LXB'), pp('L1', '/LXA')
        self.track('/LXA', [pin(16), R(-3.0, 1.75), (lxa[0], lxa[1] - 0.2)], w=0.25)
        self.track('/LXB', [pin(14), R(-3.0, 0.75), R(-3.3, 1.05), (lxb[0], UY + 1.05), lxb], w=0.25)
        # Bottom row: VBAT to its caps and ferrite; SPI/NRESET to staggered vias.
        vb = [pp(r, '/LR_VBAT') for r in ('C11', 'C12', 'FB1')]
        self.track('/LR_VBAT', [pin(17), vb[0]], w=0.25)
        self.track('/LR_VBAT', [vb[0], vb[2]], w=0.3)
        for ref in ('C11', 'C12'):
            g = pp(ref, 'GND')
            gnd(ref, (g[0], g[1] + 0.85))
        f = pp('FB1', '+3V3')
        self.track('+3V3', [f, (f[0], f[1] + 0.85)], w=0.3)
        self.via('+3V3', (f[0], f[1] + 0.85))
        for n, net, y in ((20, '/LR_NRESET', 3.55), (21, '/LR_MISO', 4.45), (22, '/LR_MOSI', 3.55),
                          (23, '/LR_SCK', 4.45), (24, '/LR_NSS', 3.55)):
            p = pin(n)
            sig(net, [p, (p[0], UY + y)])
        sig('/LR_BUSY', [pin(25), R(2.7, 1.75), R(2.7, 3.4)])

    def usb_c(self):
        """Join the duplicated USB-C pads (the autorouter cannot thread the 0.5 mm pitch)."""
        J = self.fps['J1']

        def pad(num):
            p = J.FindPadByNumber(num).GetPosition()
            return (pcbnew.ToMM(p.x), pcbnew.ToMM(p.y))

        inner = pad('A6')[0] + 0.725  # inner end of the signal pads
        # VBUS: via next to each VBUS pad, joined on B.Cu underneath the connector.
        v1, v2 = pad('A4'), pad('A9')
        a, b = (inner + 1.0, v1[1]), (inner + 1.0, v2[1])
        self.track('VBUS', [v1, a], w=0.5)
        self.track('VBUS', [v2, b], w=0.5)
        self.via('VBUS', a)
        self.via('VBUS', b)
        self.track('VBUS', [a, (inner - 0.9, a[1]), (inner - 0.9, b[1]), b], w=0.5, layer=pcbnew.B_Cu)
        # GND pads to the plane
        for num, dy in (('A1', -0.15), ('A12', 0.15)):
            g = pad(num)
            at = (inner + 0.8, g[1] + dy * 6)
            self.track('GND', [g, at], w=0.4)
            self.via('GND', at)
        # D-: B7 and A7 drop to vias and are joined on B.Cu; D+: A6 and B6 joined on F.Cu.
        dn1, dn2, dp1, dp2 = pad('B7'), pad('A7'), pad('A6'), pad('B6')
        va, vb = (inner + 0.75, dn1[1]), (inner + 1.65, dn2[1])
        self.track('/USB_DN', [dn1, va], w=0.2)
        self.track('/USB_DN', [dn2, vb], w=0.2)
        self.via('/USB_DN', va, 0.5, 0.25)
        self.via('/USB_DN', vb, 0.5, 0.25)
        self.track('/USB_DN', [va, (va[0], vb[1] - 0.45), (vb[0] - 0.45, vb[1] - 0.45), vb], w=0.2, layer=pcbnew.B_Cu)
        xj = inner + 2.45
        self.track('/USB_DP', [dp1, (xj, dp1[1]), (xj, dp2[1]), dp2], w=0.2)


    def plane_fanout(self):
        """Give every SMD pad on +3V3 / GND its own via to the inner plane."""
        T = pcbnew.ToMM
        vp = ViaPlacer(self.board)
        skip = {'U6', 'J1', 'J5', 'J6'} | {i[0] for i in RF_PARTS}
        connected = set()
        for t in self.board.GetTracks():
            if t.GetNetname() in ('+3V3', 'GND'):
                for q in (t.GetStart(), t.GetEnd()):
                    connected.add((t.GetNetname(), round(T(q.x), 2), round(T(q.y), 2)))
        failed = []
        for fp in self.board.GetFootprints():
            ref = fp.GetReference()
            if ref in skip:
                continue
            c = fp.GetPosition()
            cx, cy = T(c.x), T(c.y)
            for pad in fp.Pads():
                net = pad.GetNetname()
                if net not in ('+3V3', 'GND') or pad.GetAttribute() != pcbnew.PAD_ATTRIB_SMD:
                    continue
                px, py = T(pad.GetPosition().x), T(pad.GetPosition().y)
                if (net, round(px, 2), round(py, 2)) in connected:
                    continue
                bb = pad.GetBoundingBox()
                hw_x, hw_y = T(bb.GetWidth()) / 2, T(bb.GetHeight()) / 2
                if ref == 'U5' and pad.GetNumber() == '41':
                    continue  # the module footprint already has thermal vias in its EPAD
                dx, dy = px - cx, py - cy
                if abs(dx) >= abs(dy):
                    dirs = [(math.copysign(1, dx or 1), 0), (0, 1), (0, -1), (-math.copysign(1, dx or 1), 0)]
                else:
                    dirs = [(0, math.copysign(1, dy)), (1, 0), (-1, 0), (0, -math.copysign(1, dy))]
                r = 0.3 if net == '+3V3' else 0.25
                placed = False
                for d in (0.0, 0.25, 0.5, 0.8, 1.2, 1.6):
                    for ux, uy in dirs:
                        ext = (hw_x if ux else hw_y) + r + 0.15 + d
                        for side in (0.0, 0.5, -0.5):
                            q = (px + ux * ext + (side if not ux else 0), py + uy * ext + (side if ux else 0))
                            if vp.via_ok(net, q, r, own_ref=ref) and vp.stub_ok(net, (px, py), q, 0.15):
                                self.track(net, [(px, py), q], w=0.3)
                                self.via(net, q, 2 * r, r)
                                vp.add(net, q, r)
                                vp.add_seg(net, (px, py), q, 0.15)
                                placed = True
                                break
                        if placed:
                            break
                    if placed:
                        break
                if not placed:
                    failed.append(f'{ref}.{pad.GetNumber()}')
        if failed:
            print('plane fanout: no via spot for', ', '.join(failed))


    def silkscreen(self):
        """Hide reference designators of small parts on silk (they stay on F.Fab for the
        assembly drawing) and add functional labels."""
        keep = ('U6', 'J1', 'U2', 'U3', 'U4')
        for ref, fp in self.fps.items():
            fld = fp.Reference()
            if ref.startswith('H') or ref not in keep:
                fld.SetVisible(False)
            else:
                fld.SetTextSize(pcbnew.VECTOR2I(MM(0.8), MM(0.8)))
                fld.SetTextThickness(MM(0.12))
        labels = [
            # Pin 1 (+, square pad) is the left-hand terminal pin.
            ('5V', (105.5, 135.6), 0.9, 0),
            ('+', (103.0, 136.0), 1.0, 0),
            ('-', (108.0, 136.0), 1.0, 0),
            ('3V3', (117.0, 135.9), 0.9, 0),
            ('+', (114.5, 136.0), 1.0, 0),
            ('-', (119.5, 136.0), 1.0, 0),
            ('915 MHz', (BX1 - 5.6, UY + 9.0), 0.8, 0),
            ('2.4 GHz', (BX1 - 5.6, UY - 9.0), 0.8, 0),
            ('RESET', (125.6, 137.6), 0.8, 0),
            ('BOOT', (131.6, 137.6), 0.8, 0),
            ('GPIO 1:3V3 2:5V 17-20:GND', (148.0, 139.7), 0.8, 0),
            ('USR', (147.8, 129.5), 0.8, 0),
            ('PWR', (151.6, 129.5), 0.8, 0),
        ]
        # Board name on the bottom silkscreen (mirrored so it reads correctly from below).
        t = pcbnew.PCB_TEXT(self.board)
        t.SetText('LR2021 + ESP32-S3  rev 1.2')
        t.SetPosition(V(((BX0 + BX1) / 2, BY1 - 9.0)))
        t.SetLayer(pcbnew.B_SilkS)
        t.SetTextSize(pcbnew.VECTOR2I(MM(1.2), MM(1.2)))
        t.SetTextThickness(MM(0.18))
        t.SetMirrored(True)
        self.board.Add(t)
        for text, (x, y), size, rot in labels:
            t = pcbnew.PCB_TEXT(self.board)
            t.SetText(text)
            t.SetPosition(V((x, y)))
            t.SetLayer(pcbnew.F_SilkS)
            t.SetTextSize(pcbnew.VECTOR2I(MM(size), MM(size)))
            t.SetTextThickness(MM(size * 0.15))
            t.SetTextAngleDegrees(rot)
            self.board.Add(t)

    # -------------------------------------------------------------- run
    def local_joins(self):
        # Short links the autorouter keeps failing on in the tight LDO/LED corner.
        # +3V3_LDO into U3 pin 1 dips to B.Cu: the F.Cu side of U3 is taken by its own plane vias.
        c4 = self.padpos('C4', '/+3V3_LDO')
        u3 = self.padpos('U3', '/+3V3_LDO')
        top = (u3[0] - 0.3, u3[1] - 0.95)
        low = (c4[0], c4[1] + 0.87)
        self.track('/+3V3_LDO', [u3, (top[0], u3[1]), top], w=0.4)
        self.track('/+3V3_LDO', [c4, low], w=0.4)
        self.track('/+3V3_LDO', [top, (top[0], low[1]), low], w=0.3, layer=pcbnew.B_Cu)
        self.via('/+3V3_LDO', top)
        self.via('/+3V3_LDO', low)
        r3 = self.padpos('R3', '/LED_PWR')
        d4 = self.padpos('D4', '/LED_PWR')
        x = (r3[0] + d4[0]) / 2
        self.track('/LED_PWR', [r3, (x, r3[1]), (x, d4[1]), d4], w=0.25)

    def build(self):
        self.add_nets()
        self.add_footprints()
        self.outline()
        for ref, (x, y, rot) in PLACE.items():
            if ref in self.fps:
                self.place(ref, x, y, rot)
        for item in RF_PARTS:
            self.place_rf(*item)
        self.place('J6', *SMA_HF, 0)
        self.place('J5', *SMA_LF, 0)
        missing = [r for r in self.fps if r not in PLACE and r not in {i[0] for i in RF_PARTS} and r not in ('J5', 'J6')]
        if missing:
            raise SystemExit(f'unplaced: {missing}')
        self.route_rf()
        self.usb_c()
        self.local_joins()
        self.plane_fanout()
        self.silkscreen()
        self.ground_pours()
        self.board.BuildConnectivity()
        pcbnew.SaveBoard(PCB, self.board)
        # Models missing from the KiCad library point to ours (gen_3d_models.py). Done on the
        # saved text because FOOTPRINT.Models() hands Python a copy.
        text = open(PCB).read()
        for base in LOCAL_MODELS:
            text = re.sub(r'\$\{KICAD9_3DMODEL_DIR\}/[^/"]+\.3dshapes/' + re.escape(base),
                          '${KIPRJMOD}/lib/3d/' + base, text)
        open(PCB, 'w').write(text)
        print('saved', PCB)


if __name__ == '__main__':
    Builder().build()
