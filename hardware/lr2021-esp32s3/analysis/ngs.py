"""Minimal ctypes wrapper around libngspice (shared API): load a netlist, run, read vectors."""
import ctypes as C, numpy as np, os
lib = C.CDLL('/usr/lib/x86_64-linux-gnu/libngspice.so.0')
OUT = []
PF = C.CFUNCTYPE(C.c_int, C.c_char_p, C.c_int, C.c_void_p)
SF = C.CFUNCTYPE(C.c_int, C.c_char_p, C.c_int, C.c_void_p)
EF = C.CFUNCTYPE(C.c_int, C.c_int, C.c_bool, C.c_bool, C.c_int, C.c_void_p)
DF = C.CFUNCTYPE(C.c_int, C.c_void_p, C.c_int, C.c_int, C.c_void_p)
IF = C.CFUNCTYPE(C.c_int, C.c_void_p, C.c_int, C.c_void_p)
BF = C.CFUNCTYPE(C.c_int, C.c_bool, C.c_int, C.c_void_p)
_p = PF(lambda s, i, u: (OUT.append(s.decode(errors='replace')), 0)[1])
_s = SF(lambda s, i, u: 0)
_e = EF(lambda *a: 0)
_d = DF(lambda *a: 0)
_i = IF(lambda *a: 0)
_b = BF(lambda *a: 0)
lib.ngSpice_Init(_p, _s, _e, _d, _i, _b, None)
class vecinfo(C.Structure):
    _fields_ = [('name', C.c_char_p), ('type', C.c_int), ('flags', C.c_short),
                ('realdata', C.POINTER(C.c_double)), ('compdata', C.c_void_p), ('length', C.c_int)]
lib.ngGet_Vec_Info.restype = C.POINTER(vecinfo)
lib.ngSpice_CurPlot.restype = C.c_char_p
def cmd(s): return lib.ngSpice_Command(s.encode())
def run(netlist):
    OUT.clear()
    cmd('destroy all'); cmd('reset')
    lines = [l for l in netlist.strip().splitlines()]
    arr = (C.c_char_p * (len(lines) + 1))(*[l.encode() for l in lines], None)
    lib.ngSpice_Circ(arr)
    r = cmd('run')
    errs = [l for l in OUT if 'rror' in l]
    if errs: raise RuntimeError('\n'.join(errs[-10:]))
    return r
def vec(name):
    v = lib.ngGet_Vec_Info(name.encode())
    if not v: raise KeyError(name)
    return np.ctypeslib.as_array(v.contents.realdata, shape=(v.contents.length,)).copy()
