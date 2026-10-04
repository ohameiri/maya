"""Nodal (MNA) simulation of the LR2021 RF networks, built from the board netlist.

Component models (0402):
  C0G caps : ESR 0.15 ohm, ESL 0.35 nH (C17 X7R 1 nF: ESR 0.2, ESL 0.4 nH)
  Wire-wound L (LQW15AN / MWSD): Q(1 GHz) ~ 35 rising with sqrt(f), parallel C from typical SRF
  Multilayer high-Q L (MHQ1005P): Q(1 GHz) ~ 20
Chip side (not published by Semtech): PA pin driven as an ideal voltage node (harmonic
suppression is then a property of the network alone); LNA input in TX modelled as 0.5 pF;
VR_PA pin left open at RF (only the board decoupling acts); antenna port 50 ohm.
"""
import json, subprocess, numpy as np
B = __import__('os').path.join(__import__('os').path.dirname(__import__('os').path.dirname(__import__('os').path.abspath(__file__))), 'lr2021_esp32s3.kicad_pcb')
out = subprocess.run(['/usr/bin/python3', '-c', f'''
import pcbnew, json
b=pcbnew.LoadBoard("{B}")
d={{}}
for f in b.GetFootprints():
    r=f.GetReference()
    if r[0] in "LC" and not f.IsDNP() and len(f.Pads())==2:
        d[r]=(f.GetValue(), [p.GetNetname() for p in f.Pads()])
print(json.dumps(d))'''], capture_output=True, text=True).stdout.strip().splitlines()[-1]
PARTS = json.loads(out)
SRF = {1.1: 15e9, 1.5: 12e9, 1.6: 12e9, 2.4: 9e9, 3.9: 7e9, 4.7: 6.5e9, 12: 4.0e9, 18: 3.3e9, 22: 3.0e9, 24: 2.9e9}
RF_NETS = {'/VR_PA', '/RFO_LF', '/LF_A', '/LF_B', '/LF_C', '/ANT_LF', '/LF_RX', '/RFI_LF',
           '/RFO_HF', '/HF_A', '/HF_B', '/HF_C', '/ANT_HF', '/HF_RX', '/RFI_HF', 'GND'}

def val(s):
    s = s.replace('uF', 'e-6').replace('nF', 'e-9').replace('pF', 'e-12').replace('nH', 'e-9').replace('uH', 'e-6')
    return float(s)

def z_of(ref, v, f):
    w = 2 * np.pi * f
    if ref.startswith('C'):
        C = val(v); esl = 0.4e-9 if C > 100e-12 else 0.35e-9; esr = 0.2 if C > 100e-12 else 0.15
        return esr + 1j * w * esl + 1 / (1j * w * C)
    L = val(v); nh = round(L * 1e9, 1)
    q1 = 20 if ref == 'L11' else 35
    Q = q1 * np.sqrt(f / 1e9)
    zl = w * L / Q + 1j * w * L
    cp = 1 / ((2 * np.pi * SRF.get(nh, 5e9)) ** 2 * L)
    return 1 / (1 / zl + 1j * w * cp)

def solve(f, drive, loads):
    """drive: net held at 1 V. loads: {net: impedance to GND}. Returns node voltages and drive current."""
    comps = [(r, v, n) for r, (v, n) in PARTS.items() if set(n) <= RF_NETS]
    nets = sorted({n for _, _, ns in comps for n in ns} - {'GND'})
    idx = {n: i for i, n in enumerate(nets)}
    Y = np.zeros((len(nets), len(nets)), complex)
    for r, v, (a, b) in comps:
        y = 1 / z_of(r, v, f)
        for n1, n2 in ((a, b), (b, a)):
            if n1 != 'GND':
                Y[idx[n1], idx[n1]] += y
                if n2 != 'GND': Y[idx[n1], idx[n2]] -= y
    for n, z in loads.items(): Y[idx[n], idx[n]] += 1 / z(f) if callable(z) else 1 / z
    d = idx[drive]; keep = [i for i in range(len(nets)) if i != d]
    rhs = -Y[np.ix_(keep, [d])][:, 0]
    vk = np.linalg.solve(Y[np.ix_(keep, keep)], rhs)
    V = np.zeros(len(nets), complex); V[d] = 1; V[keep] = vk
    I = (Y @ V)[d]
    return {n: V[i] for n, i in idx.items()}, I

LNA_TX = lambda f: 1 / (1j * 2 * np.pi * f * 0.5e-12)
def path(band):
    if band == 'LF': return '/RFO_LF', '/ANT_LF', '/RFI_LF', 915e6
    return '/RFO_HF', '/ANT_HF', '/RFI_HF', 2450e6

def tx(band, f):
    pa, ant, lna, _ = path(band)
    V, I = solve(f, pa, {ant: 50.0, lna: LNA_TX})
    return V[ant], V[pa] / I, V[lna]
