import os
"""Power-path SPICE model of the LR2021 + ESP32-S3 board (ngspice via ngs.py).

Effective MLCC capacitance after DC-bias derating (pessimistic, typical X5R curves):
  0805 10uF 25V: 55% at 5 V, 70% at 3.3 V || 0805 22uF 25V: 55% at 3.3 V
  0402 1uF 25V: 55% at 5 V, 75% at 3.3 V   || 0402 4.7uF 10V: 40% at 3.3 V
ESP32-S3-WROOM internal 3V3 decoupling assumed 10 uF nominal -> 6 uF effective.
"""
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ngs

MODELS = '''
.model DSCH D(IS=1e-6 N=1.1 RS=0.1 CJO=110p BV=40)
'''

def ldo(name, vin, vout, vdo=0.36, gm=50.0, tss=120e-6):
    """AP7361C-33: soft-start reference (120 us), error amp gm = 50 A/V with a 3 MHz pole
    (loop crossover ~200 kHz with ~37 uF effective output capacitance), current limit 1.5 A,
    fold-back 0.4 A below 0.5 V, dropout modelled as 0.36 ohm (360 mV at 1 A)."""
    n = name
    return f'''
* --- {n}: AP7361C behavioural model
C{n}ss {n}ss 0 1u
B{n}ss 0 {n}ss I = (V({vin}) > 2.4) ? ((V({n}ss) < 1) ? 1e-6/{tss} : 0) : ((V({n}ss) > 0) ? -1e-6/20e-6 : 0)
B{n}e {n}e1 0 V = 3.3*min(1, max(0, V({n}ss))) - V({vout})
R{n}e {n}e1 {n}err 1k
C{n}e {n}err 0 53p
B{n}lm {n}lm 0 V = min((V({vout}) < 0.5) ? 0.4 : 1.5, max(0, (V({vin}) - V({vout}))/{vdo}))
B{n}o {vin} {vout} I = max(0, min({gm}*V({n}err), V({n}lm)))
R{n}q {vin} 0 50k
'''


def ideal_diode(name, vin, vout, ron=0.095):
    """LM66100 with CE tied to VOUT: on when VOUT < VIN-150 mV, off when VOUT > VIN+35 mV."""
    n = name
    return f'''
* --- {n}: LM66100 ideal diode (CE = VOUT)
C{n}st {n}st 0 1n
B{n}st 0 {n}st I = ((V({vin}) - V({vout})) > 0.15 && V({vin}) > 1.5) ? (1 - V({n}st))*1e-3 : (((V({vout}) - V({vin})) > 0.035) ? (0 - V({n}st))*1e-3 : 0)
B{n}sw {vin} {vout} I = (V({n}st) > 0.5) ? (V({vin}) - V({vout}))/{ron} : ((V({vin}) - V({vout}) > 0.45) ? (V({vin}) - V({vout}) - 0.45)/0.3 : 0)
'''

def board(vusb_cmd='DC 5', t_attach='0.5m', v5ext_cmd=None, v3ext_cmd=None, esp_cmd='0.045', lr_cmd='0.006', tstop='20m', tstep='1u'):
    """Full power tree. *_cmd are SPICE source specs (e.g. 'PWL(...)') or None (absent)."""
    t_att2 = repr(float(str(t_attach).replace('m','e-3').replace('u','e-6')) + 1e-6)
    net = f'''power path
{MODELS}
* --- USB host + 1 m cable
Vhost hostv 0 {vusb_cmd}
Rhost hostv hostb 0.05
Chost hostb 0 120u
* plug-in: switch closes at t_attach (contact closure ~1 us)
Vatt att 0 PWL(0 0 {t_attach} 0 {t_att2} 1)
Satt hostb cab0 att 0 SWATT
.model SWATT SW(Ron=0.01 Roff=1e7 Vt=0.5 Vh=0)
Rcab cab0 cab1 0.20
Lcab cab1 vbus 1u
Rvbusleak vbus 0 1Meg
D1 vbus v5 DSCH
'''
    if v5ext_cmd:
        net += f'''Vext5 e5s 0 {v5ext_cmd}
Rext5 e5s e5 0.1
D2 e5 v5 DSCH
'''
    net += f'''
* --- +5V bulk (C1 10u 0805 -> 5.5u eff, C2 1u 0402 -> 0.55u eff)
C1 v5 0 5.5u
C2 v5 0 0.55u
{ldo('U2', 'v5', 'v3ldo')}
* --- +3V3_LDO (C3 10u -> 7u eff, C4 100n)
C3 v3ldo 0 7u
C4 v3ldo 0 0.09u
{ideal_diode('U3', 'v3ldo', 'v3')}
'''
    if v3ext_cmd:
        net += f'''Vext3 e3s 0 {v3ext_cmd}
Rext3 e3s v3ext 0.05
C5 v3ext 0 7u
{ideal_diode('U4', 'v3ext', 'v3')}
'''
    net += f'''
* --- +3V3 rail: C6, C9 22u -> 12u eff each; C7, C10 100n; module internal ~6u eff
C6 v3 0 12u
C9 v3 0 12u
C710 v3 0 0.18u
Cmod v3 0 6u
Rled v3 0 1.1k
* ESP32-S3 load: programmable current once the rail is up
Vesp espi 0 {esp_cmd}
Besp v3 0 I = (V(v3) > 2.6) ? V(espi) : V(v3)/65
* --- ESP32 EN: R4 10k to +3V3, C8 1u 25V 0402 -> 0.75u eff
R4 v3 en 10k
C8 en 0 0.75u
* --- LR2021 VBAT via FB1 (BLM15AG121: 0.19 ohm DCR, ~0.4 uH below 10 MHz)
Lfb1 v3 fb1m 0.4u
Rfb1 fb1m lrv 0.19
C11 lrv 0 0.09u
C12 lrv 0 1.9u
Vlr lri 0 {lr_cmd}
Blr lrv 0 I = (V(lrv) > 1.8) ? V(lri) : 0
.tran {tstep} {tstop} 0 {tstep}
.end
'''
    return net

def sim(**kw):
    ngs.run(board(**kw))
    names = ['time', 'vbus', 'v5', 'v3ldo', 'v3', 'en', 'lrv']
    out = {n: ngs.vec(n) for n in names}
    out['i_vbus'] = ngs.vec('lcab#branch') if True else None
    for opt in ('v3ext',):
        try: out[opt] = ngs.vec(opt)
        except KeyError: pass
    return out
