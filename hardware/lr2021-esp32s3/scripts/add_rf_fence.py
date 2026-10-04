#!/usr/bin/python3
"""Add GND via fences along both sides of the 50-ohm antenna feeds (post-route step).

The grounded-coplanar feeds (/ANT_LF, /ANT_HF) need their side copper tied to the In1
ground every lambda_g/20 or so (3.4 mm at 2.45 GHz). The autorouter's stitching grid only
gives about one via every 5-6 mm next to the feeds, so this step adds vias every PITCH mm
on both sides, OFFSET mm from the track centre. A candidate is kept only when it clears
every other-net copper item on every layer, existing holes, rule areas that forbid vias
and the board edge. Zones are refilled afterwards. Runs on the routed board in place.

Usage: /usr/bin/python3 add_rf_fence.py [board.kicad_pcb]
"""
import math
import os
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(HERE), 'lr2021_esp32s3.kicad_pcb')
NETS = ('/ANT_LF', '/ANT_HF')
PITCH = 1.8          # mm along the feed
OFFSET = 0.95        # mm from track centre: 0.19 half-width + 0.2 gap + 0.25 via radius + 0.31 margin
VIA_D, VIA_DRILL = 0.5, 0.25
CLR = 0.22           # copper clearance to other nets (board rule 0.2)
HOLE_GAP = 0.3       # hole edge to hole edge
EDGE = 0.6           # via centre to board edge
MM = pcbnew.FromMM
T = pcbnew.ToMM


def seg_dist(p, a, b):
    ax, ay, bx, by = a[0], a[1], b[0], b[1]
    l2 = (bx - ax) ** 2 + (by - ay) ** 2
    u = 0 if l2 == 0 else max(0, min(1, ((p[0] - ax) * (bx - ax) + (p[1] - ay) * (by - ay)) / l2))
    return math.hypot(p[0] - ax - u * (bx - ax), p[1] - ay - u * (by - ay))


def main():
    board = pcbnew.LoadBoard(PCB)
    gnd = board.FindNet('GND')
    tracks, vias, pads, keepouts = [], [], [], []
    for t in board.GetTracks():
        if t.GetClass() == 'PCB_VIA':
            p = t.GetPosition()
            vias.append((t.GetNetname(), (T(p.x), T(p.y)), T(t.GetWidth(pcbnew.F_Cu)) / 2, T(t.GetDrillValue()) / 2))
        else:
            tracks.append((t.GetNetname(), (T(t.GetStart().x), T(t.GetStart().y)), (T(t.GetEnd().x), T(t.GetEnd().y)),
                           T(t.GetWidth()) / 2))
    for f in board.GetFootprints():
        for p in f.Pads():
            bb = p.GetBoundingBox()
            pads.append((p.GetNetname(), (T(bb.GetLeft()), T(bb.GetTop()), T(bb.GetRight()), T(bb.GetBottom())),
                         T(p.GetDrillSizeX()) / 2 if p.GetDrillSizeX() else 0))
    for z in board.Zones():
        if z.GetIsRuleArea() and z.GetDoNotAllowVias():
            keepouts.append(z)
    edge = board.GetBoardEdgesBoundingBox()
    ex0, ey0, ex1, ey1 = T(edge.GetLeft()), T(edge.GetTop()), T(edge.GetRight()), T(edge.GetBottom())
    r, rd = VIA_D / 2, VIA_DRILL / 2

    def ok(c):
        if not (ex0 + EDGE <= c[0] <= ex1 - EDGE and ey0 + EDGE <= c[1] <= ey1 - EDGE):
            return False
        for z in keepouts:
            if z.Outline().Contains(pcbnew.VECTOR2I(MM(c[0]), MM(c[1]))):
                return False
        for net, a, b, hw in tracks:
            if net != 'GND' and seg_dist(c, a, b) < r + hw + CLR:
                return False
        for net, (x0, y0, x1, y1), drill in pads:
            dx = max(x0 - c[0], 0, c[0] - x1); dy = max(y0 - c[1], 0, c[1] - y1)
            d = math.hypot(dx, dy)
            if d < r + (CLR if net != 'GND' else 0.05):
                return False
            if drill and d < rd + HOLE_GAP:
                return False
        for net, p, vr, vdr in vias:
            d = math.hypot(c[0] - p[0], c[1] - p[1])
            if d < rd + vdr + HOLE_GAP or (net != 'GND' and d < r + vr + CLR):
                return False
        return True

    added = 0
    for net in NETS:
        segs = [(a, b) for n, a, b, _ in tracks if n == net]
        for a, b in segs:
            L = math.hypot(b[0] - a[0], b[1] - a[1])
            if L < 0.5:
                continue
            ux, uy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
            nx, ny = -uy, ux
            k = max(1, int(L // PITCH))
            for i in range(k + 1):
                s = L * i / k
                for side in (1, -1):
                    c = (a[0] + ux * s + side * nx * OFFSET, a[1] + uy * s + side * ny * OFFSET)
                    # stay OFFSET away from every segment of the feed (corners, junctions)
                    if any(seg_dist(c, sa, sb) < OFFSET - 0.01 for sa, sb in segs):
                        continue
                    if not ok(c):
                        continue
                    v = pcbnew.PCB_VIA(board)
                    v.SetPosition(pcbnew.VECTOR2I(MM(c[0]), MM(c[1])))
                    v.SetWidth(MM(VIA_D)); v.SetDrill(MM(VIA_DRILL)); v.SetNet(gnd)
                    board.Add(v)
                    vias.append(('GND', c, r, rd))
                    added += 1
    filler = pcbnew.ZONE_FILLER(board)
    filler.Fill(board.Zones())
    pcbnew.SaveBoard(PCB, board)
    print(f'RF via fence: added {added} GND vias along {", ".join(NETS)}')


if __name__ == '__main__':
    main()
