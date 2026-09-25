import trimesh, numpy as np
s=trimesh.load('pioneer_fbx.glb')
def world(name):
    T,g=s.graph[name]; m=s.geometry[g].copy(); m.apply_transform(T); return m
fus=trimesh.util.concatenate([world('FUSELAGE'),world('~CS_MMVS')])
step=trimesh.util.concatenate([trimesh.load(f'stl/{n}.stl') for n in ['head','payload','rear','tail']])
# STEP(mm: X aft, Y span, Z up) -> FBX frame guess: x=Y, y=Z, z=X, scale 1/2545
S=1/2545.
P=np.array([[0,S,0,0],[0,0,S,0],[S,0,0,0],[0,0,0,1.]])
st=step.copy(); st.apply_transform(P)
# translate centers along z by matching nose
off=np.zeros(3); off[2]=fus.bounds[0][2]-st.bounds[0][2]; off[1]=fus.bounds[1][1]-st.bounds[1][1]
T0=trimesh.transformations.translation_matrix(off)@P
pts=step.sample(20000)
M,tp,cost=trimesh.registration.icp(pts, fus, initial=T0, max_iterations=60, scale=True)
print('cost',cost); print(np.round(M,6))
print('scale', np.cbrt(np.linalg.det(M[:3,:3])))
np.save('M.npy',M)
# also check nav light vs LED
nl=trimesh.load('stl/navlight.stl'); nl.apply_transform(M); print('navlight',nl.bounds.round(3), 'LED_R', world('~CS_LED_R').bounds.round(3), 'LED_L', world('~CS_LED_L').bounds.round(3))
