"""Minimal S-expression helpers for reading and writing KiCad files."""
from sexpdata import Symbol, loads as _loads


def S(x):
    """Return the name of a Symbol atom, or the value unchanged."""
    return x.value() if isinstance(x, Symbol) else x


def parse(text):
    # Disable sexpdata's nil/t handling so KiCad atoms survive unchanged.
    return _loads(text, nil=None, true=None)


def head(node):
    return S(node[0]) if isinstance(node, list) and node else None


def find(node, name):
    for it in node:
        if head(it) == name:
            return it
    return None


def find_all(node, name):
    return [it for it in node if head(it) == name]


def _atom(x):
    if isinstance(x, Symbol):
        return x.value()
    if isinstance(x, bool):
        return 'yes' if x else 'no'
    if isinstance(x, str):
        return '"' + x.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n') + '"'
    if isinstance(x, float):
        s = f'{x:.4f}'.rstrip('0').rstrip('.')
        return '0' if s in ('-0', '') else s
    return str(x)


def dumps(node, indent=0):
    """Serialize nested lists in KiCad's one-child-per-line style."""
    if not isinstance(node, list):
        return _atom(node)
    atoms = []
    i = 0
    while i < len(node) and not isinstance(node[i], list):
        atoms.append(_atom(node[i]))
        i += 1
    rest = node[i:]
    if not rest:
        return '(' + ' '.join(atoms) + ')'
    # Short lists of atoms/short children stay on one line.
    if all(not isinstance(c, list) or all(not isinstance(g, list) for g in c) for c in rest) and len(rest) <= 3:
        inner = ' '.join(atoms + [dumps(c) for c in rest])
        if len(inner) < 100:
            return '(' + inner + ')'
    pad = '\t' * (indent + 1)
    out = '(' + ' '.join(atoms)
    for c in rest:
        out += '\n' + pad + dumps(c, indent + 1)
    out += '\n' + '\t' * indent + ')'
    return out


def sym(name):
    return Symbol(name)
