import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, rfsim, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'docs', 'review')
fig, ax = plt.subplots(1, 2, figsize=(12, 4.2))
for k, band in enumerate(('LF', 'HF')):
    f0 = rfsim.path(band)[3]
    fs = np.linspace(0.3e9, 8e9, 800)
    a0 = abs(rfsim.tx(band, f0)[0])
    h = [20 * np.log10(abs(rfsim.tx(band, f)[0]) / a0) for f in fs]
    ax[k].plot(fs / 1e9, h, color='C0')
    for n in (1, 2, 3):
        ax[k].axvline(n * f0 / 1e9, color='C3' if n > 1 else 'C2', lw=0.8, ls='--')
    ax[k].set_ylim(-90, 10); ax[k].grid(alpha=.3)
    ax[k].set_title(f'{band}: PA pin -> antenna, normalised to {f0/1e6:.0f} MHz'); ax[k].set_xlabel('GHz'); ax[k].set_ylabel('dB')
fig.tight_layout(); fig.savefig(os.path.join(OUT, 'd1_rf_response.png'), dpi=110)
print('ok')
