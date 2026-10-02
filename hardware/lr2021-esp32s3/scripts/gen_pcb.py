#!/usr/bin/python3
"""Build the 4-layer PCB from the schematic netlist (KiCad 9 pcbnew API).

Stage 1 (this script): footprints, nets, outline, placement, hand-routed RF
section (50 ohm GCPW, chokes, shunt GND vias), keepouts and copper pours.
Stage 2 (route.py): Freerouting for the remaining nets, then zone fill.

Run with the system python that ships the pcbnew module:  /usr/bin/python3 gen_pcb.py
"""
import math
import os
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
MM = pcbnew.FromMM

# Board outline (mm). KiCad origin offset keeps the board inside the A4 sheet.
BX0, BY0, BX1, BY1 = 100.0, 100.0, 190.0, 165.0
CORNER_R = 2.0

# LR2021 centre; it is rotated 270 deg so its RF pins (25-32) face the right edge.
UX, UY = 158.0, 130.0
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
    # ESP32-S3 module: antenna end flush with the top edge (module is 25.5 mm tall).
    'U5': (125.0, 112.75, 0),
    'U6': (UX, UY, 270),
    # USB-C on the left edge, opening facing out.
    'J1': (103.0, 128.0, 270),
    'U1': (111.0, 125.5, 0),
    'R1': (110.5, 131.6, 0),
    'R2': (110.5, 133.2, 0),
    # Power path
    'D1': (114.0, 137.5, 0),
    'D2': (114.0, 141.5, 0),
    'D3': (114.0, 150.0, 0),
    'C1': (118.8, 137.8, 90),
    'C2': (120.6, 137.8, 90),
    'U2': (126.0, 140.5, 0),
    'C3': (131.8, 138.2, 90),
    'C4': (133.6, 138.2, 90),
    'C5': (124.0, 152.5, 0),
    'U3': (137.5, 140.0, 0),
    'U4': (137.5, 145.5, 0),
    'C6': (142.0, 140.0, 90),
    'C7': (143.8, 140.0, 90),
    # Screw terminals on the bottom edge, wire entry facing out.
    'J2': (112.0, 159.75, 180),
    'J3': (127.0, 159.75, 180),
    # ESP32 support
    'C9': (112.0, 109.6, 90),
    'C10': (114.0, 109.2, 90),
    'R4': (112.2, 113.6, 0),
    'C8': (112.2, 115.3, 0),
    'SW1': (105.5, 112.0, 0),
    'SW2': (105.5, 118.6, 0),
    'R5': (137.0, 122.5, 90),
    'D5': (141.0, 109.5, 0),
    'R6': (141.0, 111.5, 0),
    'D4': (146.0, 109.5, 0),
    'R3': (146.0, 111.5, 0),
    'J4': (135.0, 161.5, 90),
    # LR2021 support (crystal + NTC on top, SIMO on the left, VBAT below)
    'Y1': (*R(-0.6, -5.2), 270),
    'TH1': (*R(-2.6, -5.2), 90),
    'R8': (*R(-4.0, -5.2), 90),
    'C16': (*R(1.25, -7.0), 90),
    'FB3': (*R(-4.8, -2.8), 0),
    'C15': (*R(-5.0, -1.2), 0),
    'C13': (*R(-6.6, -0.2), 90),
    'L1': (*R(-4.3, 1.25), 90),
    'FB2': (*R(-6.6, 3.0), 90),
    'C11': (*R(-1.75, 4.6), 90),
    'C12': (*R(-3.2, 4.6), 90),
    'FB1': (*R(-4.8, 4.6), 90),
    'R7': (*R(0.9, 5.6), 90),
    'H1': (186.0, 104.0, 0),
    'H2': (186.0, 161.0, 0),
    'H3': (104.0, 146.0, 0),
    'H4': (154.0, 104.0, 0),
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
    ]
    return parts


RF_PARTS = _rf_parts()
SMA_HF = (BX1 - 2.1, UY - 13.0)
SMA_LF = (BX1 - 2.1, UY + 13.0)
VR_PA_IN2_X = 3.95


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
        for layer in (pcbnew.In1_Cu, pcbnew.F_Cu, pcbnew.In2_Cu, pcbnew.B_Cu):
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
            xd = j[0] - 4.0 - abs(j[1] - end[1])
            self.track(net, [end, (xd, end[1]), (j[0] - 4.0, j[1]), j])
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
                   w=0.4, layer=pcbnew.In2_Cu)
        self.track('/VR_PA', [bot_via, (UX + 3.4, l2[1]), l2], w=0.3)
        self.track('/VR_PA', [l2, c18], w=0.3)

        # ---- GND for shunt parts: short stub to a stitching via (offset from the GND pad)
        for ref, d in (('C26', (0, -1.0)), ('C28', (0, -1.0)), ('C30', (0, -1.0)), ('C31', (0, -1.0)),
                       ('D7', (0, -1.0)), ('L12', (0, 0.95)), ('C33', (0, 0.85)), ('C17', (0, -1.0)),
                       ('C18', (0, 1.0)), ('C20', (0, 1.0)), ('C22', (0, 1.0)), ('C23', (0, 1.0)),
                       ('L6', (0, 1.0)), ('D6', (0, 1.0)), ('C25', (0, -0.85)), ('C14', (-0.6, 0.9))):
            g = self.padpos(ref, 'GND')
            self.gnd_via_for(ref, (g[0] + d[0], g[1] + d[1]))
        # QFN ground pins straight into the exposed pad
        for n in (30, 15):
            p = pin(n)
            self.track('GND', [p, (UX + (p[0] - UX) * 0.6, p[1])], w=PIN_W)
        # SIMO loop kept tiny: LXB/LXA straight to the inductor
        self.track('/LXB', [pin(14), (pp('L1', '/LXB')[0], pin(14)[1])], w=PIN_W)
        self.track('/LXA', [pin(16), (pp('L1', '/LXA')[0], pin(16)[1])], w=PIN_W)
        # VDCC2 escape between the chip and the LF riser
        self.track('/VDCC', [pin(26), R(3.3, 1.25), pp('C14', '/VDCC')], w=PIN_W)
        # XTA is right above its pin
        self.track('/XTA', [pin(4), R(0.25, -3.6), pp('Y1', '/XTA')], w=0.2)

        # Stitching vias along both sides of the antenna feeds and around the SMA launch
        for end, xd, j in feeds:
            x = end[0] + 1.0
            while x < xd - 0.3:
                for s in (-1.0, 1.0):
                    self.via('GND', (x, end[1] + s))
                x += 1.6
            for dx in (-3.6, -2.0):
                for s in (-1.3, 1.3):
                    self.via('GND', (j[0] + dx, j[1] + s))
        self.rf_feeds = feeds

    # -------------------------------------------------------------- run
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
        self.ground_pours()
        self.board.BuildConnectivity()
        pcbnew.SaveBoard(PCB, self.board)
        print('saved', PCB)


if __name__ == '__main__':
    Builder().build()
