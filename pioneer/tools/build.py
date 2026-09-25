import trimesh, numpy as np, json
from PIL import Image
from trimesh.visual.material import PBRMaterial
M=np.load('M.npy'); k=np.cbrt(np.linalg.det(M[:3,:3]))
R=np.diag([1/(1000*k)]*3+[1.])      # FBX units -> metres (STEP mm/1000)
s=trimesh.load('pioneer_fbx.glb')
def fbx(name):
    T,g=s.graph[name]; m=s.geometry[g].copy(); m.apply_transform(R@T); return m
tex=Image.open('Pioneer.tga').convert('RGB').resize((1024,1024), Image.LANCZOS)
def mat(c, rough=0.55, metal=0.0):
    return PBRMaterial(baseColorFactor=[int(255*x) for x in c]+[255], roughnessFactor=rough, metallicFactor=metal)
scene=trimesh.Scene(); meta=[]
def add(name, m, group, source, desc):
    scene.add_geometry(m, node_name=name, geom_name=name); meta.append(dict(name=name, group=group, source=source, desc=desc, tris=len(m.faces)))
cad={'head':('Nose cone','机头 Pioneer head'),'payload':('Payload compartment','载荷舱 Pioneer payload compartment'),
     'rear':('Fuselage rear','机身尾部 Pioneer fuselage rear'),'tail':('Vertical tail','垂尾 Pioneer tail')}
white=mat((0.93,0.93,0.91),0.45)
for n,(title,src) in cad.items():
    m=trimesh.load(f'stl/{n}.stl'); m.apply_transform(R@M); m.visual=trimesh.visual.TextureVisuals(material=white)
    add(title, m, 'CAD fuselage', 'STEP', src)
    if n=='payload': pay=m
    if n=='rear': rear=m
    if n=='head': head=m
# nav lights: snap to wing-tip LED sockets of the airframe model, mirror for left
nl=trimesh.load('stl/navlight.stl'); nl.apply_transform(R@M)
for side,led,col in [('right','~CS_LED_R',(0.1,0.85,0.3)),('left','~CS_LED_L',(0.9,0.12,0.1))]:
    m=nl.copy()
    if side=='left':
        m.apply_transform(np.diag([-1,1,1,1.])); m.invert()
    tgt=fbx(led).bounds.mean(0); m.apply_translation(tgt-m.bounds.mean(0))
    m.visual=trimesh.visual.TextureVisuals(material=mat(col,0.3))
    add(f'Nav light {side}', m, 'CAD fuselage' if False else 'CAD nav lights','STEP','航灯外壳 navigation light housing')
# airframe parts from RealFlight model
fx={'FUSELAGE':('Mid fuselage','Fuselage'),'~CS_LMW':('Left wing','Wing'),'~CS_RMW':('Right wing','Wing'),
 '~CS_LMA':('Left aileron','Control surfaces'),'~CS_RMA':('Right aileron','Control surfaces'),
 '~CS_LMHS':('Left stabilizer','Tail'),'~CS_RMHS':('Right stabilizer','Tail'),'~CS_LME':('Left elevator','Control surfaces'),'~CS_RME':('Right elevator','Control surfaces'),
 '~CS_MMR':('Rudder','Control surfaces'),'~CS_BOOM_L':('Left boom','VTOL'),'~CS_BOOM_R':('Right boom','VTOL'),
 '~CS_LG':('Left landing gear','Landing gear'),'~CS_RG':('Right landing gear','Landing gear'),
 '~CS_ENGINE_P':('Cruise propeller','Propulsion'),'~CS_SPINNER_P':('Cruise spinner','Propulsion')}
for c in ['FL','FR','RL','RR']:
    fx[f'~CS_ENGINE_{c}']=(f'Rotor {c} propeller','VTOL'); fx[f'~CS_MOUNT_{c}']=(f'Rotor {c} motor','VTOL'); fx[f'~CS_SPINNER_{c}']=(f'Rotor {c} spinner','VTOL')
for key,(title,group) in fx.items():
    m=fbx(key)
    if key=='FUSELAGE':   # keep only the section between the CAD payload bay and CAD rear fuselage
        z0=pay.bounds[1][2]-0.01; z1=rear.bounds[0][2]+0.01
        m=m.slice_plane([0,0,z0],[0,0,1]); m=m.slice_plane([0,0,z1],[0,0,-1])
    m.visual.material=PBRMaterial(baseColorTexture=tex, roughnessFactor=0.5, metallicFactor=0.0, doubleSided=True)
    add(title, m, group, 'RealFlight FBX', key.strip('~'))
    if key=='FUSELAGE':   # top hatch over the open CAD nose + payload bay
        h=fbx(key); ztop=max(head.bounds[1][1],pay.bounds[1][1])-0.025
        h=h.slice_plane([0,0,pay.bounds[1][2]],[0,0,-1]); h=h.slice_plane([0,ztop,0],[0,1,0]).slice_plane([0,ztop,0],[0,1,0])
        h.visual.material=m.visual.material
        add('Top hatch', h, 'Fuselage', 'RealFlight FBX', 'FUSELAGE (top)')
b=scene.bounds; print('bounds m', b.round(3).tolist(), 'size', (b[1]-b[0]).round(3).tolist())
scene.export('pioneer_full.glb', include_normals=True); json.dump(meta, open('parts.json','w'), ensure_ascii=False, indent=1)
