#!/usr/bin/python3
"""Stage 2: autoroute the non-RF nets with Freerouting, then pour ground.

The hand-routed RF section is locked and fenced off with temporary keepouts so
the autorouter cannot run signals between the matching-network rows. Only the
In1 ground plane is present during routing (Freerouting treats a pour as a
plane that blocks the whole layer); the other ground pours are added afterwards.

Usage: /usr/bin/python3 route.py [path/to/freerouting.jar]
"""
import os
import subprocess
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gen_pcb as G  # noqa: E402

JAR = sys.argv[1] if len(sys.argv) > 1 else '/tmp/claude-0/tools/freerouting.jar'
WORK = '/tmp/claude-0/route'
MM = pcbnew.FromMM


def rect(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def main():
    os.makedirs(WORK, exist_ok=True)
    board = pcbnew.LoadBoard(G.PCB)
    b = G.Builder.__new__(G.Builder)  # reuse the zone helper without rebuilding
    b.board = board
    b.netinfo = {str(k): v for k, v in board.GetNetsByName().items()}

    # Keep only the In1 ground plane while routing.
    for z in list(board.Zones()):
        if not z.GetIsRuleArea() and z.GetLayer() != pcbnew.In1_Cu:
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
    # Inner-layer VR_PA link column.
    temp.append(b.zone(None, [pcbnew.In2_Cu], rect(ux + 3.55, uy - 11.6, ux + 4.35, uy + 11.6), rule_area=True))

    dsn, ses = os.path.join(WORK, 'board.dsn'), os.path.join(WORK, 'board.ses')
    for f in (dsn, ses):
        if os.path.exists(f):
            os.remove(f)
    if not pcbnew.ExportSpecctraDSN(board, dsn):
        raise SystemExit('DSN export failed')
    cmd = ['java', '-jar', JAR, '-de', dsn, '-do', ses, '-mp', '200', '-mt', '4', '--gui.enabled=false']
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
    m = 0.3
    outline = rect(G.BX0 + m, G.BY0 + m, G.BX1 - m, G.BY1 - m)
    for layer in (pcbnew.F_Cu, pcbnew.In2_Cu, pcbnew.B_Cu):
        b.zone('GND', layer, outline, priority=0, clearance=0.2, name=f'GND_{board.GetLayerName(layer)}')
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    pcbnew.SaveBoard(G.PCB, board)
    print('routed and saved', G.PCB)


if __name__ == '__main__':
    main()
