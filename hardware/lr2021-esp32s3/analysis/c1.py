import os
import sys, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pwr, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
r = pwr.sim(vusb_cmd='DC 5.0', t_attach='0.5m', tstop='30m', tstep='0.5u')
t=r['time']*1e3; i=-r['i_vbus'] if np.mean(r['i_vbus'][t>1])<0 else r['i_vbus']
# metrics
ipk=i.max(); m=(t>0.5)&(t<2.5); q=np.trapezoid(np.clip(i[m]-i[-1],0,None), r["time"][m])*1e6
t3=t[np.argmax(r['v3']>3.0)]; ten=t[np.argmax(r['en']>0.75*3.3)]
print(f'inrush peak {ipk:.2f} A, charge in first 2 ms {q:.0f} uC')
print(f'+3V3 reaches 3.0 V at {t3:.3f} ms; EN reaches 0.75*VDD at {ten:.2f} ms -> EN delay after rail OK by {ten-t3:.2f} ms (ESP32 needs >= 0.05 ms)')
print(f'final: VBUS {r["vbus"][-1]:.3f} V, +5V {r["v5"][-1]:.3f}, +3V3_LDO {r["v3ldo"][-1]:.3f}, +3V3 {r["v3"][-1]:.3f}, LR_VBAT {r["lrv"][-1]:.3f}')
fig,ax=plt.subplots(2,1,figsize=(10,7),sharex=True)
for k,lab in (('vbus','VBUS'),('v5','+5V'),('v3ldo','+3V3_LDO'),('v3','+3V3'),('en','ESP_EN')): ax[0].plot(t,r[k],label=lab)
ax[0].set_ylabel('V'); ax[0].legend(); ax[0].grid(alpha=.3); ax[0].set_title('C1: USB plug-in power-up (host 5.0 V, 1 m cable)')
ax[1].plot(t,i,color='C3'); ax[1].set_ylabel('I_VBUS [A]'); ax[1].set_xlabel('ms'); ax[1].grid(alpha=.3)
ax[1].set_xlim(0,20)
fig.tight_layout(); fig.savefig(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'docs', 'review', 'c1_powerup.png'),dpi=110)
fig,ax=plt.subplots(figsize=(10,4)); m=(t>0.45)&(t<1.3)
ax.plot(t[m],i[m],color='C3'); ax.set_ylabel('I_VBUS [A]'); ax.set_xlabel('ms'); ax.grid(alpha=.3); ax.set_title('C3: inrush detail')
ax2=ax.twinx(); ax2.plot(t[m],r['v5'][m],'C1--',label='+5V'); ax2.plot(t[m],r['v3'][m],'C2--',label='+3V3'); ax2.set_ylabel('V'); ax2.legend(loc='lower right')
fig.tight_layout(); fig.savefig(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'docs', 'review', 'c3_inrush.png'),dpi=110)
