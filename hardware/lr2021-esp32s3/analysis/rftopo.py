import re, json, collections, sys
import networkx as nx
from networkx.algorithms import isomorphism as iso

def parse_ref(path):
    t = open(path).read()
    comps = {}
    for m in re.finditer(r'\n\t\(footprint "([^"]+)"(.*?)\n\t\)', t, re.S):
        blk = m.group(2)
        ref = re.search(r'\(property "Reference" "([^"]+)"', blk).group(1)
        val = re.search(r'\(property "ALTIUM_VALUE" "([^"]*)"', blk)
        val = val.group(1) if val else re.search(r'\(property "Value" "([^"]*)"', blk).group(1)
        pads = {}
        for pm in re.finditer(r'\(pad "([^"]*)"(.*?)\n\t\t\)', blk, re.S):
            n = re.search(r'\(net "([^"]*)"\)', pm.group(2))
            if n and pm.group(1): pads.setdefault(pm.group(1), n.group(1))
        comps[ref] = (val, pads)
    return comps

def parse_ours(path):
    import subprocess
    out = subprocess.run(['/usr/bin/python3', '-c', f'''
import pcbnew, json
b=pcbnew.LoadBoard("{path}")
d={{}}
for f in b.GetFootprints():
    pads={{}}
    for p in f.Pads():
        if p.GetNumber(): pads.setdefault(p.GetNumber(), p.GetNetname())
    d[f.GetReference()]=(f.GetValue(), pads, bool(f.IsDNP()))
print(json.dumps(d))
'''], capture_output=True, text=True).stdout
    d = json.loads(out.strip().splitlines()[-1])
    return {k: (('NC' if v[2] else v[0]), v[1]) for k, v in d.items()}

def norm(v):
    v = v.strip().replace('µ', 'u').replace(' ', '')
    if v.upper() in ('NC', 'DNP', 'NF', 'N/C'): return 'NC'
    m = re.match(r'^([0-9.]+)(p|n|u)?(F|H)?$', v, re.I)
    if m:
        num = float(m.group(1)); unit = (m.group(2) or '').lower(); kind = (m.group(3) or '').upper()
        return f'{num:g}{unit}{kind}'
    return v

def build(comps, chip, ants, gndnames):
    pinrole = {'1': 'VR_PA', '27': 'RFO_LF', '28': 'RFO_LF', '29': 'RFI_LF', '31': 'RFI_HF', '32': 'RFO_HF'}
    netlabel = {}
    for p, role in pinrole.items():
        netlabel[comps[chip][1][p]] = role
    for a, lab in ants.items():
        netlabel[comps[a][1]['1']] = lab
    for g in gndnames: netlabel[g] = 'GND'
    # adjacency: nets -> two-terminal passives
    two = {r: c for r, c in comps.items() if r[0] in 'LCDF' and len(c[1]) == 2 and not r.startswith('FB')}
    netcomp = collections.defaultdict(set)
    for r, (v, pads) in two.items():
        for n in pads.values(): netcomp[n].add(r)
    start = [comps[chip][1][p] for p in pinrole]
    seen_n, seen_c, todo = set(), set(), list(start)
    while todo:
        n = todo.pop()
        if n in seen_n: continue
        seen_n.add(n)
        if netlabel.get(n) in ('GND',) : continue
        for r in netcomp[n]:
            if r in seen_c: continue
            seen_c.add(r)
            for m in two[r][1].values():
                if m not in seen_n: todo.append(m)
    G = nx.Graph()
    for n in seen_n: G.add_node(('n', n), kind='n', label=netlabel.get(n, 'net'))
    for r in seen_c:
        v, pads = two[r]
        G.add_node(('c', r), kind='c', label=r[0] + ':' + norm(v))
        for m in pads.values():
            G.add_edge(('c', r), ('n', m))
    return G

ref = parse_ref(sys.argv[1]); ours = parse_ours(sys.argv[2])
gr = build(ref, 'U1', {'ANT_LF1': 'ANT_LF', 'ANT_HF1': 'ANT_HF'}, ['GND'])
go = build(ours, 'U6', {'J5': 'ANT_LF', 'J6': 'ANT_HF'}, ['GND'])
print('reference RF graph:', sum(1 for n in gr if n[0]=='c'), 'components', sum(1 for n in gr if n[0]=='n'), 'nets')
print('our RF graph      :', sum(1 for n in go if n[0]=='c'), 'components', sum(1 for n in go if n[0]=='n'), 'nets')
gm = iso.GraphMatcher(gr, go, node_match=lambda a, b: a['label'] == b['label'])
if gm.is_isomorphic():
    print('TOPOLOGY + VALUES: IDENTICAL (graph isomorphic with matching labels)')
    for a, b in sorted(gm.mapping.items()):
        if a[0] == 'c': print(f'   ref {a[1]:6} -> ours {b[1]:6} {gr.nodes[a]["label"]}')
else:
    print('NOT isomorphic; label multisets:')
    ca = collections.Counter(d['label'] for _, d in gr.nodes(data=True)); cb = collections.Counter(d['label'] for _, d in go.nodes(data=True))
    print('  only in ref :', dict(ca - cb)); print('  only in ours:', dict(cb - ca))
    # topology without values: parts by type (L/C/D), nets by role
    gm2 = iso.GraphMatcher(gr, go, node_match=lambda a, b: a['kind'] == b['kind'] and (
        a['label'][0] == b['label'][0] if a['kind'] == 'c' else a['label'] == b['label']))
    print('  topology only (types, no values) isomorphic:', gm2.is_isomorphic())

print('\n--- second pass: diodes compared by type only ---')
for G in (gr, go):
    for n, d in G.nodes(data=True):
        if d['label'].startswith('D:'): d['label'] = 'D'
gm = iso.GraphMatcher(gr, go, node_match=lambda a, b: a['label'] == b['label'])
print('isomorphic with all L/C values and net roles matching:', gm.is_isomorphic())
if gm.is_isomorphic():
    m = gm.mapping
    pairs = sorted((a[1], b[1], gr.nodes[a]['label']) for a, b in m.items() if a[0] == 'c')
    for a, b, lab in pairs: print(f'   ref {a:7} -> ours {b:6} {lab}')
    roles = sorted((gr.nodes[a]['label'], a[1], b[1]) for a, b in m.items() if a[0] == 'n' and gr.nodes[a]['label'] != 'net')
    for lab, a, b in roles: print(f'   net role {lab:7}: ref {a:22} -> ours {b}')
