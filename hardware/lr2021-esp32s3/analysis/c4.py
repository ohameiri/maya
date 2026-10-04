import os
import sys, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pwr, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
esp='DC 0.045'; lr='DC 0.12'   # LoRa TX running during the switchover (worst load on the rail)
cases = {
 'a) USB unplugged, 5V terminal present': dict(vusb_cmd='PWL(0 5 5m 5 5.001m 0)', v5ext_cmd='DC 5.0'),
 'b) 5V terminal removed, USB present':   dict(vusb_cmd='DC 5.0', v5ext_cmd='PWL(0 5 5m 5 5.001m 0)'),
 'c) 3V3 ext (3.40 V) removed, USB present': dict(vusb_cmd='DC 5.0', v3ext_cmd='PWL(0 3.4 5m 3.4 5.001m 0)'),
 'd) 3V3 ext (3.30 V) removed, USB present': dict(vusb_cmd='DC 5.0', v3ext_cmd='PWL(0 3.3 5m 3.3 5.001m 0)'),
 'e) 3V3 ext (3.40 V) plugged, USB present': dict(vusb_cmd='DC 5.0', v3ext_cmd='PWL(0 0 5m 0 5.001m 3.4)'),
 'f) USB unplugged, 3V3 ext (3.30 V) present': dict(vusb_cmd='PWL(0 5 5m 5 5.001m 0)', v3ext_cmd='DC 3.3'),
}
fig, ax = plt.subplots(len(cases), 1, figsize=(10, 2.2*len(cases)), sharex=True)
for k, (name, kw) in enumerate(cases.items()):
    r = pwr.sim(t_attach='0.1m', esp_cmd=esp, lr_cmd=lr, tstop='8m', tstep='0.2u', **kw)
    t = r['time']*1e3; m = (t > 4.5) & (t < 8)
    pre = r['v3'][(t > 4.0) & (t < 4.9)].mean()
    print(f'{name:45s}: +3V3 before {pre:.3f} V, min after {r["v3"][t>5].min():.3f} V, max after {r["v3"][t>5].max():.3f} V, final {r["v3"][-1]:.3f} V')
    ax[k].plot(t[m], r['v3'][m], color='C2', label='+3V3'); ax[k].plot(t[m], r['v3ldo'][m], '--', color='C1', label='+3V3_LDO')
    if 'v3ext' in r: ax[k].plot(t[m], r['v3ext'][m], ':', color='C0', label='+3V3_EXT')
    ax[k].set_ylim(2.8, 3.5); ax[k].axhline(3.0, color='r', lw=.7); ax[k].set_title(name, fontsize=9); ax[k].grid(alpha=.3); ax[k].legend(fontsize=7, loc='lower left')
ax[-1].set_xlabel('ms'); fig.tight_layout(); fig.savefig(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'docs', 'review', 'c4_switchover.png'), dpi=100)
