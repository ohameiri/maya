import os
import sys, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pwr, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
# ESP32: 45 mA idle, Wi-Fi TX burst 355 mA (2 us edge) 5.0-7.0 ms; LR2021: RX 6 mA, PA ramp to 120 mA at 4.9 ms (10 us) until 8 ms
esp = 'PWL(0 0.045 5m 0.045 5.002m 0.355 7m 0.355 7.002m 0.045)'
lr  = 'PWL(0 0.006 4.9m 0.006 4.91m 0.12 8m 0.12 8.01m 0.006)'
res = {}
fig, ax = plt.subplots(2, 1, figsize=(10, 7), sharex=True)
for host, ls in ((5.0, '-'), (4.75, '--'), (4.40, ':')):
    r = pwr.sim(vusb_cmd=f'DC {host}', t_attach='0.1m', esp_cmd=esp, lr_cmd=lr, tstop='10m', tstep='0.5u')
    t = r['time'] * 1e3; m = t > 3
    res[host] = dict(v3min=r['v3'][m].min(), lrmin=r['lrv'][m].min(), v5min=r['v5'][m].min(), vbusmin=r['vbus'][m].min(),
                     v3ldo_min=r['v3ldo'][m].min())
    ax[0].plot(t[m], r['v3'][m], ls, color='C2', label=f'+3V3 (host {host} V)')
    ax[0].plot(t[m], r['lrv'][m], ls, color='C4', label=f'LR_VBAT (host {host} V)')
    ax[1].plot(t[m], r['v5'][m], ls, color='C1', label=f'+5V (host {host} V)')
for h, d in res.items():
    print(f"host {h:.2f} V: min VBUS {d['vbusmin']:.3f}  +5V {d['v5min']:.3f}  +3V3_LDO {d['v3ldo_min']:.3f}  +3V3 {d['v3min']:.3f}  LR_VBAT {d['lrmin']:.3f}")
ax[0].axhline(3.0, color='r', lw=0.8); ax[0].text(3.05, 3.005, 'ESP32-S3 min 3.0 V', color='r', fontsize=8)
ax[0].set_ylabel('V'); ax[0].legend(fontsize=7, ncol=2); ax[0].grid(alpha=.3)
ax[0].set_title('C2: LoRa +22 dBm (120 mA) + Wi-Fi TX burst (355 mA) on USB power')
ax[1].set_ylabel('V'); ax[1].set_xlabel('ms'); ax[1].legend(fontsize=7); ax[1].grid(alpha=.3)
fig.tight_layout(); fig.savefig(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'docs', 'review', 'c2_tx_droop.png'), dpi=110)
