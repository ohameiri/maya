#!/usr/bin/python3
"""Export fabrication and documentation outputs into ../fab and ../docs.

- Gerbers + Excellon drill (zipped for JLCPCB)
- BOM (full, and JLCPCB format) and pick-and-place (JLCPCB format)
- Schematic PDF, PCB layer PDF and PNG previews
"""
import collections
import csv
import os
import shutil
import subprocess
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gen_pcb as G  # noqa: E402

PROJ = G.PROJ_DIR
NAME = G.PROJECT
SCH = os.path.join(PROJ, f'{NAME}.kicad_sch')
PCB = G.PCB
FAB = os.path.join(PROJ, 'fab')
DOCS = os.path.join(PROJ, 'docs')
GERBER_DIR = os.path.join(FAB, 'gerbers')
LAYERS = 'F.Cu,In1.Cu,In2.Cu,B.Cu,F.Paste,B.Paste,F.Silkscreen,B.Silkscreen,F.Mask,B.Mask,Edge.Cuts'


def cli(*args):
    subprocess.run(['kicad-cli', *args], check=True, capture_output=True)


def describe(ref, value, fp):
    """Purchasing description for generic passives."""
    name = fp.split(':')[-1].split('_')
    pkg = name[1] if len(name) > 1 else name[0]
    if ref.startswith('C'):
        if value.endswith('pF'):
            return f'{value} 50V C0G/NP0 {pkg}'
        if value in ('100nF', '1nF', '10nF'):
            return f'{value} 16V X7R {pkg}'
        return f'{value} 10V X5R {pkg}' if pkg == '0402' else f'{value} 16V X5R {pkg}'
    if ref.startswith('R'):
        return f'{value} 1% {pkg}'
    return value


def bom():
    comps, _ = G.read_netlist()
    groups = collections.OrderedDict()
    for ref in sorted(comps, key=lambda r: (''.join(c for c in r if c.isalpha()), int(''.join(c for c in r if c.isdigit()) or 0))):
        c = comps[ref]
        if c['fp'].startswith('MountingHole'):
            continue
        f = c['fields']
        key = (c['value'], c['fp'], f.get('MPN', ''), f.get('LCSC', ''), f.get('Spec', ''), c['dnp'])
        groups.setdefault(key, []).append(ref)
    with open(os.path.join(FAB, f'{NAME}_bom.csv'), 'w', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['Qty', 'References', 'Value', 'Description', 'Footprint', 'MPN', 'LCSC', 'Notes', 'Populate'])
        for (val, fp, mpn, lcsc, spec, dnp), refs in groups.items():
            w.writerow([len(refs), ' '.join(refs), val, describe(refs[0], val, fp), fp.split(':')[1], mpn, lcsc,
                        spec, 'DNP' if dnp else 'yes'])
    with open(os.path.join(FAB, f'{NAME}_bom_jlcpcb.csv'), 'w', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['Comment', 'Designator', 'Footprint', 'LCSC Part #'])
        for (val, fp, mpn, lcsc, spec, dnp), refs in groups.items():
            if dnp:
                continue
            w.writerow([mpn or describe(refs[0], val, fp), ','.join(refs), fp.split(':')[1], lcsc])


# JLCPCB places each LCSC part using its own (EasyEDA) footprint, whose zero rotation,
# pin-1 corner and origin can differ from KiCad's. Measured per LCSC part by overlaying
# the EasyEDA pads on ours (see README, "Pre-production checks").
#   rot: degrees added to the KiCad rotation
#   shift: (x, y) mm in the footprint's own frame (KiCad orientation 0, y up)
#   center: place at the pad centroid (KiCad origin is pin 1, JLC origin is the body centre)
JLC_FIX = {
    'C2286': dict(rot=180),                  # KT-0603R LED: EasyEDA pin 1 (cathode) on the right
    'C7519': dict(rot=270),                  # USBLC6-2SC6, SOT-23-6
    'C2869734': dict(rot=270),               # LM66100, SC-70-6
    'C500795': dict(rot=180),                # AP7361C, SOT-223
    'C5199907': dict(rot=270),               # SMA edge mount
    'C42372518': dict(rot=270, center=True), # 2x10 header
    'C474881': dict(center=True),            # KF301 screw terminal
    'C3013946': dict(shift=(0.0, -0.48)),    # ESP32-S3-WROOM-1U
    'C165948': dict(shift=(0.0, 1.53)),      # HRO TYPE-C-31-M-12
}


def _lcsc_by_ref():
    out = {}
    with open(os.path.join(FAB, f'{NAME}_bom_jlcpcb.csv')) as fh:
        for r in csv.DictReader(fh):
            for ref in r['Designator'].split(','):
                out[ref.strip()] = r['LCSC Part #']
    return out


def cpl():
    import math
    import pcbnew
    raw = os.path.join(FAB, 'pos_raw.csv')
    cli('pcb', 'export', 'pos', '--format', 'csv', '--units', 'mm', '--side', 'front', '--exclude-dnp', '-o', raw, PCB)
    board = pcbnew.LoadBoard(PCB)
    lcsc = _lcsc_by_ref()
    with open(raw) as fh, open(os.path.join(FAB, f'{NAME}_cpl_jlcpcb.csv'), 'w', newline='') as out:
        w = csv.writer(out)
        w.writerow(['Designator', 'Mid X', 'Mid Y', 'Layer', 'Rotation'])
        for row in csv.DictReader(fh):
            if row['Package'].startswith('MountingHole'):
                continue
            x, y, r = float(row['PosX']), float(row['PosY']), float(row['Rot'])   # y up, rotation CCW
            fix = JLC_FIX.get(lcsc.get(row['Ref']), {})
            if fix.get('center'):
                pads = board.FindFootprintByReference(row['Ref']).Pads()
                x = sum(pcbnew.ToMM(p.GetPosition().x) for p in pads) / len(pads)
                y = -sum(pcbnew.ToMM(p.GetPosition().y) for p in pads) / len(pads)
            if 'shift' in fix:
                a = math.radians(r)
                sx, sy = fix['shift']
                x += sx * math.cos(a) - sy * math.sin(a)
                y += sx * math.sin(a) + sy * math.cos(a)
            r = (r + fix.get('rot', 0)) % 360
            w.writerow([row['Ref'], f"{x:.4f}mm", f"{y:.4f}mm",
                        'Top' if row['Side'] == 'top' else 'Bottom', f"{r:.1f}"])
    os.remove(raw)


def gerbers():
    shutil.rmtree(GERBER_DIR, ignore_errors=True)
    os.makedirs(GERBER_DIR)
    cli('pcb', 'export', 'gerbers', '--layers', LAYERS, '--subtract-soldermask', '-o', GERBER_DIR + '/', PCB)
    cli('pcb', 'export', 'drill', '--format', 'excellon', '--excellon-separate-th', '--generate-map',
        '--map-format', 'pdf', '-o', GERBER_DIR + '/', PCB)
    zpath = os.path.join(FAB, f'{NAME}_gerbers.zip')
    with zipfile.ZipFile(zpath, 'w', zipfile.ZIP_DEFLATED) as z:
        for f in sorted(os.listdir(GERBER_DIR)):
            z.write(os.path.join(GERBER_DIR, f), f)


def docs():
    os.makedirs(DOCS, exist_ok=True)
    cli('sch', 'export', 'pdf', '-o', os.path.join(DOCS, f'{NAME}_schematic.pdf'), SCH)
    # --mode-multipage writes <dir>/<board>.pdf, so render into a temp dir and move it.
    tmpdir = '/tmp/claude-0/pcbpdf'
    shutil.rmtree(tmpdir, ignore_errors=True)
    cli('pcb', 'export', 'pdf', '--mode-multipage', '--include-border-title', '--layers',
        'F.Cu,In1.Cu,In2.Cu,B.Cu,F.Silkscreen,F.Fab', '--common-layers', 'Edge.Cuts',
        '-o', tmpdir + '/', PCB)
    shutil.move(os.path.join(tmpdir, f'{NAME}.pdf'), os.path.join(DOCS, f'{NAME}_pcb_layers.pdf'))
    # PNG previews (board area only) for the README.
    tmp = '/tmp/claude-0/preview.pdf'
    dpi = 300
    px = lambda mm: int(round(mm * dpi / 25.4))  # noqa: E731
    x0, y0 = px(G.BX0 - 1), px(G.BY0 - 1)
    w, h = px(G.BX1 - G.BX0 + 2), px(G.BY1 - G.BY0 + 2)
    for name, layers in (('top', 'F.Cu,F.Silkscreen,Edge.Cuts'), ('inner2', 'In2.Cu,Edge.Cuts'),
                         ('bottom', 'B.Cu,Edge.Cuts'), ('assembly', 'F.Fab,F.Silkscreen,Edge.Cuts')):
        cli('pcb', 'export', 'pdf', '--mode-single', '--layers', layers, '-o', tmp, PCB)
        out = os.path.join(DOCS, f'pcb_{name}')
        subprocess.run(['pdftoppm', '-r', str(dpi), '-png', '-singlefile', '-x', str(x0), '-y', str(y0),
                        '-W', str(w), '-H', str(h), tmp, out], check=True)


def main():
    os.makedirs(FAB, exist_ok=True)
    gerbers()
    bom()
    cpl()
    docs()
    print('fabrication outputs in', FAB, 'and', DOCS)


if __name__ == '__main__':
    main()
