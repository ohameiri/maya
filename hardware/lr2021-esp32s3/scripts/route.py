#!/usr/bin/python3
"""Stage 2: autoroute the non-RF nets with Freerouting, then pour ground.

The hand-routed RF section is locked and fenced off with temporary keepouts so
the autorouter cannot run signals between the matching-network rows. Only the
inner planes (In1 GND, In2 +3V3) are present during routing (Freerouting treats a
pour as a plane that blocks the whole layer); the outer ground pours are added afterwards.

Usage: /usr/bin/python3 route.py [path/to/freerouting.jar]
"""
import math
import os
import subprocess
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gen_pcb as G  # noqa: E402

JAR = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] != '--finish' else '/tmp/claude-0/tools/freerouting-1.9.0.jar'
WORK = '/tmp/claude-0/route'
MM = pcbnew.FromMM


def rect(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def remove_single_layer_vias(board):
    """Drop signal vias that ended up with copper on only one layer (a via counts as
    used on a layer when a track of its net ends at it or passes over it)."""
    segs = [(t.GetNetname(), t.GetLayer(), t.GetStart(), t.GetEnd(), t.GetWidth())
            for t in board.GetTracks() if t.GetClass() != 'PCB_VIA']

    def touches(p, a, b, hw):
        ax, ay, bx, by = a.x, a.y, b.x, b.y
        dx, dy = bx - ax, by - ay
        L = dx * dx + dy * dy
        t = 0 if L == 0 else max(0.0, min(1.0, ((p.x - ax) * dx + (p.y - ay) * dy) / L))
        return math.hypot(p.x - ax - t * dx, p.y - ay - t * dy) <= hw

    doomed = []
    for v in [t for t in board.GetTracks() if t.GetClass() == 'PCB_VIA']:
        if v.GetNetname() in ('GND', '+3V3'):
            continue
        p, net = v.GetPosition(), v.GetNetname()
        layers = {layer for n, layer, a, b, w in segs if n == net and touches(p, a, b, w / 2)}
        if len(layers) <= 1:
            doomed.append(v)
    board.BuildConnectivity()
    conn = board.GetConnectivity()
    removed = 0
    for v in doomed:
        before = conn.GetUnconnectedCount(False)
        net, pos, w, drill = v.GetNetCode(), v.GetPosition(), v.GetWidth(pcbnew.F_Cu), v.GetDrillValue()
        locked = v.IsLocked()
        board.Delete(v)
        board.BuildConnectivity()
        conn = board.GetConnectivity()
        if conn.GetUnconnectedCount(False) > before:  # it was needed after all: put it back
            nv = pcbnew.PCB_VIA(board)
            nv.SetPosition(pos)
            nv.SetWidth(w)
            nv.SetDrill(drill)
            nv.SetNetCode(net)
            nv.SetLocked(locked)
            board.Add(nv)
            board.BuildConnectivity()
            conn = board.GetConnectivity()
        else:
            removed += 1
    print('removed single-layer vias:', removed, 'of', len(doomed), 'candidates')


def stitch(board, pitch=4.0):
    """GND stitching vias on a grid wherever they fit (ties the outer pours to In1)."""
    vp = G.ViaPlacer(board)
    b = G.Builder.__new__(G.Builder)
    b.board = board
    b.netinfo = {str(k): v for k, v in board.GetNetsByName().items()}
    n = 0
    y = G.BY0 + 2.0
    while y < G.BY1 - 1.5:
        x = G.BX0 + 2.0
        while x < G.BX1 - 1.5:
            if vp.via_ok('GND', (x, y), 0.3, margin=1.0) and not vp.pads_near((x, y), 0.3 + 0.3):
                b.via('GND', (x, y), lock=False)
                vp.add('GND', (x, y), 0.3)
                n += 1
            x += pitch
        y += pitch
    print('stitching vias:', n)


def main():
    os.makedirs(WORK, exist_ok=True)
    board = pcbnew.LoadBoard(G.PCB)
    b = G.Builder.__new__(G.Builder)  # reuse the zone helper without rebuilding
    b.board = board
    b.netinfo = {str(k): v for k, v in board.GetNetsByName().items()}

    # Keep only the inner planes (In1 GND, In2 +3V3) while routing.
    for z in list(board.Zones()):
        if not z.GetIsRuleArea() and z.GetLayer() not in (pcbnew.In1_Cu, pcbnew.In2_Cu):
            board.Remove(z)

    all_cu = [pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.B_Cu]
    temp = []
    ux, uy = G.UX, G.UY
    # RF rows, chokes and feed lines (everything right of the TX risers).
    temp.append(b.zone(None, all_cu, rect(ux + 4.05, uy - 11.6, G.BX1 - 0.2, uy + 11.6), rule_area=True,
                       name='TMP_RF'))
    # SMA launch areas.
    for (x, y) in (G.SMA_HF, G.SMA_LF):
        temp.append(b.zone(None, all_cu, rect(x - 8.0, y - 3.5, G.BX1 - 0.2, y + 3.5), rule_area=True))
    # Gap between the QFN RF pins and the risers (only the hand-routed escapes live here).
    temp.append(b.zone(None, all_cu, rect(ux + 2.9, uy - 2.2, ux + 4.05, uy + 0.95), rule_area=True))
    # Edge margin so routed copper keeps the 0.3 mm copper-to-edge rule.
    e = 0.5
    for r_ in (rect(G.BX0, G.BY0, G.BX1, G.BY0 + e), rect(G.BX0, G.BY1 - e, G.BX1, G.BY1),
               rect(G.BX0, G.BY0, G.BX0 + e, G.BY1), rect(G.BX1 - e, G.BY0, G.BX1, G.BY1)):
        temp.append(b.zone(None, [pcbnew.F_Cu, pcbnew.B_Cu], r_, rule_area=True))
    # Bottom-layer VR_PA link column.
    temp.append(b.zone(None, [pcbnew.B_Cu], rect(ux + 3.55, uy - 11.6, ux + 4.35, uy + 11.6), rule_area=True))

    dsn, ses = os.path.join(WORK, 'board.dsn'), os.path.join(WORK, 'board.ses')
    for f in (dsn, ses):
        if os.path.exists(f):
            os.remove(f)
    if not pcbnew.ExportSpecctraDSN(board, dsn):
        raise SystemExit('DSN export failed')
    # Mark the inner layers as power planes so the autorouter keeps signals on L1/L4
    # (KiCad exports every copper layer as a signal layer).
    text = open(dsn).read()
    for layer in ('In1.Cu', 'In2.Cu'):
        text = text.replace(f'(layer {layer}\n      (type signal)', f'(layer {layer}\n      (type power)')
    open(dsn, 'w').write(text)
    passes = os.environ.get('FR_PASSES', '60')
    cmd = ['xvfb-run', '-a', 'java', '-jar', JAR, '-de', dsn, '-do', ses, '-mp', passes, '-oit', '100', '-mt', '1']
    print('running', ' '.join(cmd), flush=True)
    log = subprocess.run(cmd, capture_output=True, text=True)
    open(os.path.join(WORK, 'freerouting.log'), 'w').write(log.stdout + log.stderr)
    if not os.path.exists(ses):
        print(log.stdout[-3000:], log.stderr[-3000:])
        raise SystemExit('Freerouting produced no session file')
    if not pcbnew.ImportSpecctraSES(board, ses):
        raise SystemExit('SES import failed')

    for z in temp:
        board.Remove(z)
    pcbnew.SaveBoard(G.PCB, board)
    # The SWIG track iterators misbehave after ImportSpecctraSES, so finish in a fresh process.
    subprocess.run([sys.executable, os.path.abspath(__file__), '--finish'], check=True)
    print('routed and saved', G.PCB)


def finish():
    board = pcbnew.LoadBoard(G.PCB)
    remove_single_layer_vias(board)
    stitch(board)
    b = G.Builder.__new__(G.Builder)
    b.board = board
    b.netinfo = {str(k): v for k, v in board.GetNetsByName().items()}
    m = 0.3
    outline = rect(G.BX0 + m, G.BY0 + m, G.BX1 - m, G.BY1 - m)
    for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
        b.zone('GND', layer, outline, priority=0, clearance=0.2, name=f'GND_{board.GetLayerName(layer)}')
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    pcbnew.SaveBoard(G.PCB, board)


if __name__ == '__main__':
    if '--finish' in sys.argv:
        finish()
    else:
        main()
