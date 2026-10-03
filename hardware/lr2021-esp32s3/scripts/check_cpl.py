#!/usr/bin/python3
"""Check the JLCPCB pick-and-place file against JLCPCB's own footprints.

For every part in fab/*_cpl_jlcpcb.csv, fetch the EasyEDA footprint of its LCSC part,
place it the way JLCPCB will (CPL position and rotation) and compare it with our pads:

- numbered: the same pad numbers must land on each other (catches reversed LEDs and
  diodes, and ICs turned 90/180 degrees)
- geometric: when the numbering differs (connectors, buttons), every EasyEDA pad must
  land on one of ours

Prints one line per part; exits non-zero if any part is off by more than TOL mm.
Needs network access to easyeda.com. Responses are cached in /tmp/easyeda_cache.
"""
import csv
import json
import math
import os
import subprocess
import sys
import time

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
NAME = 'lr2021_esp32s3'
CACHE = '/tmp/easyeda_cache'
TOL = 0.5


def easyeda_pads(lcsc):
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, lcsc + '.json')
    if not os.path.exists(path):
        url = f'https://easyeda.com/api/products/{lcsc}/components?version=6.4.19.5'
        out = subprocess.run(['curl', '-sS', '-m', '30', url], capture_output=True, text=True).stdout
        with open(path, 'w') as fh:
            fh.write(out)
        time.sleep(0.5)
    with open(path) as fh:
        res = json.load(fh).get('result')
    if not res:
        return None, []
    ds = res['packageDetail']['dataStr']
    ox, oy = float(ds['head']['x']), float(ds['head']['y'])
    pads = []
    for s in ds['shape']:
        if s.startswith('PAD~'):
            f = s.split('~')
            pads.append((f[8], (float(f[2]) - ox) * 0.254, -(float(f[3]) - oy) * 0.254))   # mm, y up
    return res['packageDetail']['title'], pads


def rotate(x, y, deg):
    a = math.radians(deg)
    return x * math.cos(a) - y * math.sin(a), x * math.sin(a) + y * math.cos(a)


def main():
    board = pcbnew.LoadBoard(os.path.join(PROJ, f'{NAME}.kicad_pcb'))
    lcsc = {}
    with open(os.path.join(PROJ, 'fab', f'{NAME}_bom_jlcpcb.csv')) as fh:
        for r in csv.DictReader(fh):
            for ref in r['Designator'].split(','):
                lcsc[ref.strip()] = r['LCSC Part #']
    bad = 0
    with open(os.path.join(PROJ, 'fab', f'{NAME}_cpl_jlcpcb.csv')) as fh:
        rows = list(csv.DictReader(fh))
    for r in rows:
        ref = r['Designator']
        X, Y, R = float(r['Mid X'][:-2]), float(r['Mid Y'][:-2]), float(r['Rotation'])
        title, ep = easyeda_pads(lcsc[ref])
        if not ep:
            print(f'{ref:5} {lcsc[ref]:>10}  no EasyEDA footprint (check in the JLCPCB preview)')
            continue
        ours = {}
        for p in board.FindFootprintByReference(ref).Pads():
            q = p.GetPosition()
            ours.setdefault(p.GetNumber(), []).append((pcbnew.ToMM(q.x), -pcbnew.ToMM(q.y)))
        placed = [(n,) + tuple(a + b for a, b in zip(rotate(x, y, R), (X, Y))) for n, x, y in ep]
        theirs = {}
        for n, x, y in placed:
            theirs.setdefault(n, []).append((x, y))
        centre = lambda v: (sum(a for a, _ in v) / len(v), sum(b for _, b in v) / len(v))  # noqa: E731
        common = [n for n in theirs if n in ours and len(theirs[n]) == len(ours[n])]
        if common and len(common) == len(theirs):
            err, how = max(math.dist(centre(theirs[n]), centre(ours[n])) for n in common), 'numbered'
        else:
            flat = [q for v in ours.values() for q in v]
            err, how = max(min(math.dist((x, y), q) for q in flat) for _, x, y in placed), 'geometric'
        ok = err <= TOL
        bad += not ok
        print(f'{ref:5} {lcsc[ref]:>10} {title[:36]:36} {how:9} max pad error {err:5.2f} mm  {"OK" if ok else "WRONG"}')
    print(f'{len(rows)} parts, {bad} misplaced')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
