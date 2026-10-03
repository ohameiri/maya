#!/usr/bin/env python3
"""Generate the KiCad 9 schematic for the LR2021 + ESP32-S3 board.

Every component pin gets a short wire stub that ends in a net label or a power
symbol, so the whole netlist is defined by the tables below. Run ERC after
regenerating:  kicad-cli sch erc lr2021_esp32s3.kicad_sch
"""
import math
import os
import uuid

from sexpr import S, dumps, find, find_all, head, parse, sym

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ_DIR = os.path.dirname(HERE)
PROJECT = 'lr2021_esp32s3'
KICAD_SYM = '/usr/share/kicad/symbols'
CUSTOM_LIB = os.path.join(PROJ_DIR, 'lib', f'{PROJECT}.kicad_sym')
NS = uuid.UUID('6f1c2a8e-35a1-4c1e-9d0e-2b5a3c4d1e01')
ROOT_UUID = str(uuid.uuid5(NS, 'root'))
STUB = 2.54
POWER_NETS = {'GND': 'power:GND', '+3V3': 'power:+3V3', '+5V': 'power:+5V', 'VBUS': 'power:VBUS'}

_uid_counter = [0]


def uid(tag=None):
    _uid_counter[0] += 1
    return str(uuid.uuid5(NS, f'{tag}-{_uid_counter[0]}'))


# ---------------------------------------------------------------- LR2021 symbol
# (number, name, electrical type, side, slot). Slots count downward from the top
# on the left/right sides and left-to-right on the top/bottom sides.
LR2021_PINS = [
    ('17', 'VBAT', 'power_in', 'L', 0),
    ('1', 'VR_PA', 'power_out', 'L', 1),
    ('13', 'VPAX1', 'power_out', 'L', 2),
    ('2', 'VPAX2', 'passive', 'L', 3),
    ('12', 'VDCC1', 'power_out', 'L', 4),
    ('26', 'VDCC2', 'passive', 'L', 5),
    ('16', 'LXA', 'passive', 'L', 6),
    ('14', 'LXB', 'passive', 'L', 7),
    ('4', 'XTA', 'passive', 'L', 9),
    ('5', 'XTB', 'passive', 'L', 10),
    ('6', 'VTCXO/VNTC', 'output', 'L', 11),
    ('3', 'NTC', 'input', 'L', 12),
    ('24', 'NSS', 'input', 'R', 0),
    ('23', 'SCK', 'input', 'R', 1),
    ('22', 'MOSI', 'input', 'R', 2),
    ('21', 'MISO', 'output', 'R', 3),
    ('20', 'NRESET', 'input', 'R', 4),
    ('25', 'BUSY', 'output', 'R', 5),
    ('19', 'DIO5', 'bidirectional', 'R', 7),
    ('18', 'DIO6', 'bidirectional', 'R', 8),
    ('11', 'DIO7', 'bidirectional', 'R', 9),
    ('10', 'DIO8', 'bidirectional', 'R', 10),
    ('9', 'DIO9', 'bidirectional', 'R', 11),
    ('8', 'DIO10', 'bidirectional', 'R', 12),
    ('7', 'DIO11', 'bidirectional', 'R', 13),
    ('28', 'RFO_LF1', 'passive', 'T', 0),
    ('27', 'RFO_LF2', 'passive', 'T', 1),
    ('29', 'RFI_LF', 'passive', 'T', 2),
    ('31', 'RFI_HF', 'passive', 'T', 4),
    ('32', 'RFO_HF', 'passive', 'T', 5),
    ('30', 'GND', 'power_in', 'B', 0),
    ('15', 'GND_DCC', 'power_in', 'B', 1),
    ('33', 'GND_EP', 'power_in', 'B', 2),
]


def lr2021_symbol():
    W, H, PL = 15.24, 20.32, 5.08  # half width, half height, pin length
    items = [sym('symbol'), 'LR2021',
             [sym('pin_names'), [sym('offset'), 1.016]],
             [sym('exclude_from_sim'), sym('no')], [sym('in_bom'), sym('yes')], [sym('on_board'), sym('yes')]]

    def prop(name, val, x, y, hide=False):
        eff = [sym('effects'), [sym('font'), [sym('size'), 1.27, 1.27]]]
        if hide:
            eff.append([sym('hide'), sym('yes')])
        return [sym('property'), name, val, [sym('at'), x, y, 0], eff]

    items += [prop('Reference', 'U', -W, H + 1.27),
              prop('Value', 'LR2021', W, H + 1.27),
              prop('Footprint', 'Package_DFN_QFN:QFN-32-1EP_5x5mm_P0.5mm_EP3.7x3.7mm_ThermalVias', 0, -H - 5.08, True),
              prop('Datasheet', 'https://www.semtech.com/products/wireless-rf/lora-plus/lr2021', 0, -H - 7.62, True),
              prop('Description', 'Semtech LR2021 LoRa Plus multi-band transceiver, sub-GHz/1.9-2.1GHz/2.4GHz, QFN-32 5x5mm', 0, -H - 10.16, True),
              prop('ki_keywords', 'LoRa transceiver Semtech LR2021 LoRaPlus', 0, 0, True)]
    body = [sym('symbol'), 'LR2021_0_1',
            [sym('rectangle'), [sym('start'), -W, H], [sym('end'), W, -H],
             [sym('stroke'), [sym('width'), 0.254], [sym('type'), sym('default')]],
             [sym('fill'), [sym('type'), sym('background')]]]]
    pins = [sym('symbol'), 'LR2021_1_1']
    for num, name, etype, side, slot in LR2021_PINS:
        if side == 'L':
            x, y, a = -W - PL, H - 2.54 - slot * 2.54, 0
        elif side == 'R':
            x, y, a = W + PL, H - 2.54 - slot * 2.54, 180
        elif side == 'T':
            x, y, a = -6.35 + slot * 2.54, H + PL, 270
        else:
            x, y, a = -5.08 + slot * 5.08, -H - PL, 90
        pins.append([sym('pin'), sym(etype), sym('line'), [sym('at'), round(x, 3), round(y, 3), a], [sym('length'), PL],
                     [sym('name'), name, [sym('effects'), [sym('font'), [sym('size'), 1.27, 1.27]]]],
                     [sym('number'), num, [sym('effects'), [sym('font'), [sym('size'), 1.27, 1.27]]]]])
    items += [body, pins, [sym('embedded_fonts'), sym('no')]]
    return items


def write_custom_lib():
    os.makedirs(os.path.dirname(CUSTOM_LIB), exist_ok=True)
    lib = [sym('kicad_symbol_lib'), [sym('version'), 20241209], [sym('generator'), 'gen_schematic.py'],
           [sym('generator_version'), '9.0'], lr2021_symbol()]
    with open(CUSTOM_LIB, 'w') as f:
        f.write(dumps(lib) + '\n')


# ---------------------------------------------------------------- library access
_libs = {}


def lib_symbols(lib):
    if lib not in _libs:
        path = CUSTOM_LIB if lib == PROJECT else f'{KICAD_SYM}/{lib}.kicad_sym'
        data = parse(open(path).read())
        _libs[lib] = {it[1]: it for it in data if head(it) == 'symbol'}
    return _libs[lib]


def flat_symbol(lib, name):
    """Return the symbol with any `extends` resolved, named `name`."""
    s = lib_symbols(lib)[name]
    ext = find(s, 'extends')
    if not ext:
        return s
    parent = flat_symbol(lib, ext[1])
    pname = parent[1]
    child_props = [it for it in s if head(it) == 'property']
    child_names = {p[1] for p in child_props}
    out = [sym('symbol'), name]
    for it in parent[2:]:
        h = head(it)
        if h in ('property', 'symbol', 'embedded_fonts'):
            continue
        out.append(it)
    out += child_props
    out += [p for p in find_all(parent, 'property') if p[1] not in child_names]
    for sub in find_all(parent, 'symbol'):
        sub = list(sub)
        sub[1] = name + sub[1][len(pname):]
        out.append(sub)
    out.append([sym('embedded_fonts'), sym('no')])
    return out


def symbol_pins(lib_id):
    lib, name = lib_id.split(':')
    s = flat_symbol(lib, name)
    pins = []
    for sub in find_all(s, 'symbol'):
        for p in find_all(sub, 'pin'):
            at = find(p, 'at')
            pins.append({'num': find(p, 'number')[1], 'name': find(p, 'name')[1], 'type': S(p[1]),
                         'x': float(at[1]), 'y': float(at[2]), 'a': float(at[3])})
    return pins


def embedded(lib_id):
    lib, name = lib_id.split(':')
    s = list(flat_symbol(lib, name))
    s[1] = lib_id
    return s


# ---------------------------------------------------------------- geometry
def xform(px, py, rot):
    """Library point (y up) -> schematic offset (y down) for a symbol rotation."""
    x, y = px, -py
    r = math.radians(rot)
    return (round(x * math.cos(r) + y * math.sin(r), 4), round(-x * math.sin(r) + y * math.cos(r), 4))


def outward(pin_angle, rot):
    a = math.radians(pin_angle + 180)
    dx, dy = xform(math.cos(a), math.sin(a), rot)
    return (round(dx), round(dy))


# ---------------------------------------------------------------- design tables
parts = []
NC = 'NC'


def part(ref, lib_id, value, fp, x, y, rot=0, nets=None, dnp=False, ref_pos=None, val_pos=None, **fields):
    x, y = round(round(x / 2.54) * 2.54, 2), round(round(y / 2.54) * 2.54, 2)  # snap to the 100 mil grid
    parts.append(dict(ref=ref, lib_id=lib_id, value=value, fp=fp, x=x, y=y, rot=rot, nets=nets or {}, dnp=dnp,
                      ref_pos=ref_pos, val_pos=val_pos, fields=fields))


C0402 = 'Capacitor_SMD:C_0402_1005Metric'
C0805 = 'Capacitor_SMD:C_0805_2012Metric'
R0402 = 'Resistor_SMD:R_0402_1005Metric'
L0402 = 'Inductor_SMD:L_0402_1005Metric'


def vcap(ref, val, x, y, top, bot='GND', fp=C0402, **kw):
    part(ref, 'Device:C', val, fp, x, y, 0, {'1': top, '2': bot}, **kw)


def hcap(ref, val, x, y, left, right, fp=C0402, **kw):
    part(ref, 'Device:C', val, fp, x, y, 90, {'1': left, '2': right}, **kw)


def vres(ref, val, x, y, top, bot, fp=R0402, **kw):
    part(ref, 'Device:R', val, fp, x, y, 0, {'1': top, '2': bot}, **kw)


def vind(ref, val, x, y, top, bot, fp=L0402, **kw):
    part(ref, 'Device:L', val, fp, x, y, 0, {'1': top, '2': bot}, **kw)


def hind(ref, val, x, y, left, right, fp=L0402, **kw):
    part(ref, 'Device:L', val, fp, x, y, 90, {'1': left, '2': right}, **kw)


def vfb(ref, x, y, top, bot, val='120R', **kw):
    kw.setdefault('MPN', 'BLM15AG121SN1D')
    kw.setdefault('LCSC', 'C85812')
    part(ref, 'Device:FerriteBead', val, L0402, x, y, 0, {'1': top, '2': bot}, **kw)


RFC = dict(Spec='C0G/NP0, +/-0.1pF (<10pF) or 2%, Murata GRM15/GJM15 high-Q')
RFL = dict(Spec='Wire-wound high-Q, +/-2% or +/-0.1nH, Murata LQW15AN series')

# ---- Power input & regulation --------------------------------------------------
part('J1', 'Connector:USB_C_Receptacle_USB2.0_16P', 'USB-C', 'Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12',
     40, 70, 0, {'A4': 'VBUS', 'A9': 'VBUS', 'B4': 'VBUS', 'B9': 'VBUS', 'A5': 'CC1', 'B5': 'CC2',
                 'A7': 'USB_DN', 'B7': 'USB_DN', 'A6': 'USB_DP', 'B6': 'USB_DP', 'A8': NC, 'B8': NC,
                 'A1': 'GND', 'A12': 'GND', 'B1': 'GND', 'B12': 'GND', 'S1': 'GND'},
     MPN='HRO TYPE-C-31-M-12', LCSC='C165948')
vres('R1', '5.1k', 80, 82, 'CC1', 'GND')
vres('R2', '5.1k', 92, 82, 'CC2', 'GND')
part('U1', 'Power_Protection:USBLC6-2SC6', 'USBLC6-2SC6', 'Package_TO_SOT_SMD:SOT-23-6', 120, 72, 0,
     {'1': 'USB_DN', '6': 'USB_DN', '3': 'USB_DP', '4': 'USB_DP', '5': 'VBUS', '2': 'GND'},
     MPN='USBLC6-2SC6', LCSC='C7519')
part('J2', 'Connector:Screw_Terminal_01x02', '5V IN', 'TerminalBlock_Phoenix:TerminalBlock_Phoenix_MKDS-1,5-2_1x02_P5.00mm_Horizontal',
     45, 125, 0, {'1': '+5V_EXT', '2': 'GND'}, MPN='KF301-5.0-2P', LCSC='C474881')
part('D3', 'Device:D_TVS', 'SMF5.0CA', 'Diode_SMD:D_SOD-123F', 70, 128, 90, {'2': '+5V_EXT', '1': 'GND'},
     MPN='SMF5.0CA', LCSC='C2980402')
part('D1', 'Device:D_Schottky', 'B5819W', 'Diode_SMD:D_SOD-123', 150, 40, 180, {'2': 'VBUS', '1': '+5V'},
     MPN='B5819W', LCSC='C8598')
part('D2', 'Device:D_Schottky', 'B5819W', 'Diode_SMD:D_SOD-123', 150, 60, 180, {'2': '+5V_EXT', '1': '+5V'},
     MPN='B5819W', LCSC='C8598')
vcap('C1', '10uF', 175, 62, '+5V', fp=C0805)
vcap('C2', '100nF', 187, 62, '+5V')
part('U2', 'Regulator_Linear:AP7361C-33E', 'AP7361C-33E', 'Package_TO_SOT_SMD:SOT-223-3_TabPin2', 215, 42, 0,
     {'1': '+5V', '2': 'GND', '3': '+3V3_LDO'}, MPN='AP7361C-33E-13', LCSC='C500795')
vcap('C3', '10uF', 240, 62, '+3V3_LDO', fp=C0805)
vcap('C4', '100nF', 252, 62, '+3V3_LDO')
part('J3', 'Connector:Screw_Terminal_01x02', '3V3 IN', 'TerminalBlock_Phoenix:TerminalBlock_Phoenix_MKDS-1,5-2_1x02_P5.00mm_Horizontal',
     150, 125, 0, {'1': '+3V3_EXT', '2': 'GND'}, MPN='KF301-5.0-2P', LCSC='C474881')
vcap('C5', '10uF', 175, 128, '+3V3_EXT', fp=C0805)
part('U3', 'Power_Management:LM66100DCK', 'LM66100', 'Package_TO_SOT_SMD:SOT-363_SC-70-6', 280, 45, 0,
     {'1': '+3V3_LDO', '3': '+3V3', '4': NC, '2': 'GND', '6': '+3V3', '5': NC}, MPN='LM66100DCKR', LCSC='C2869734')
part('U4', 'Power_Management:LM66100DCK', 'LM66100', 'Package_TO_SOT_SMD:SOT-363_SC-70-6', 280, 95, 0,
     {'1': '+3V3_EXT', '3': '+3V3', '4': NC, '2': 'GND', '6': '+3V3', '5': NC}, MPN='LM66100DCKR', LCSC='C2869734')
vcap('C6', '22uF', 305, 62, '+3V3', fp=C0805)
vcap('C7', '100nF', 317, 62, '+3V3')
vres('R3', '1k', 305, 105, '+3V3', 'LED_PWR')
part('D4', 'Device:LED', 'GREEN', 'LED_SMD:LED_0603_1608Metric', 305, 135, 90, {'2': 'LED_PWR', '1': 'GND'})

# ---- ESP32-S3 ------------------------------------------------------------------
ESP_NETS = {
    '2': '+3V3', '1': 'GND', '40': 'GND', '41': 'GND', '3': 'ESP_EN', '27': 'BOOT',
    '13': 'USB_DN', '14': 'USB_DP',
    '17': 'GPIO9', '18': 'LR_NSS', '19': 'LR_MOSI', '20': 'LR_SCK', '21': 'LR_MISO', '22': 'LR_NRESET',
    '23': 'LR_BUSY', '24': 'LR_DIO9', '25': 'GPIO48', '12': NC, '38': 'LED_USER',
    '39': 'GPIO1', '4': 'GPIO4', '5': 'GPIO5', '6': 'GPIO6', '7': 'GPIO7', '8': NC, '9': NC,
    '10': NC, '11': NC, '31': 'GPIO38', '32': 'GPIO39', '33': 'GPIO40', '34': 'GPIO41',
    '35': 'GPIO42', '37': 'U0TXD', '36': 'U0RXD',
    '15': NC, '16': NC, '26': NC, '28': NC, '29': NC, '30': NC,
}
part('U5', 'RF_Module:ESP32-S3-WROOM-1', 'ESP32-S3-WROOM-1-N16R8', 'RF_Module:ESP32-S3-WROOM-1', 420, 100, 0, ESP_NETS,
     MPN='ESP32-S3-WROOM-1-N16R8', LCSC='C2913202')
vres('R4', '10k', 345, 30, '+3V3', 'ESP_EN')
vcap('C8', '1uF', 357, 30, 'ESP_EN')
part('SW1', 'Switch:SW_Push', 'RESET', 'Button_Switch_SMD:SW_Push_1P1T_XKB_TS-1187A', 340, 55, 0, {'1': 'ESP_EN', '2': 'GND'},
     MPN='TS-1187A-B-A-B', LCSC='C318884')
vres('R5', '10k', 345, 85, '+3V3', 'BOOT')
part('SW2', 'Switch:SW_Push', 'BOOT', 'Button_Switch_SMD:SW_Push_1P1T_XKB_TS-1187A', 340, 110, 0, {'1': 'BOOT', '2': 'GND'},
     MPN='TS-1187A-B-A-B', LCSC='C318884')
vcap('C9', '22uF', 470, 30, '+3V3', fp=C0805)
vcap('C10', '100nF', 482, 30, '+3V3')
vres('R6', '1k', 480, 135, 'LED_USER', 'LED_USER_A')
part('D5', 'Device:LED', 'BLUE', 'LED_SMD:LED_0603_1608Metric', 480, 165, 90, {'2': 'LED_USER_A', '1': 'GND'})
vres('R7', '10k', 494, 30, '+3V3', 'LR_NSS')
HDR = {'1': '+3V3', '2': '+5V', '3': 'GPIO4', '4': 'GPIO5', '5': 'GPIO6', '6': 'GPIO7', '7': 'GPIO9', '8': 'GPIO48',
       '9': 'GPIO38', '10': 'GPIO39', '11': 'GPIO40', '12': 'GPIO41', '13': 'GPIO42', '14': 'GPIO1',
       '15': 'U0TXD', '16': 'U0RXD', '17': 'GND', '18': 'GND', '19': 'GND', '20': 'GND'}
part('J4', 'Connector_Generic:Conn_02x10_Odd_Even', 'GPIO', 'Connector_PinHeader_2.54mm:PinHeader_2x10_P2.54mm_Vertical',
     545, 100, 0, HDR)

# ---- LR2021 core -----------------------------------------------------------------
LR_NETS = {
    '17': 'LR_VBAT', '1': 'VR_PA', '13': 'VPAX1', '2': 'VPAX', '12': 'VDCC1', '26': 'VDCC', '16': 'LXA', '14': 'LXB',
    '4': 'XTA', '5': 'XTB', '6': 'LR_VNTC', '3': 'LR_NTC',
    '24': 'LR_NSS', '23': 'LR_SCK', '22': 'LR_MOSI', '21': 'LR_MISO', '20': 'LR_NRESET', '25': 'LR_BUSY',
    '19': NC, '18': NC, '11': NC, '10': NC, '9': 'LR_DIO9', '8': NC, '7': NC,
    '28': 'RFO_LF', '27': 'RFO_LF', '29': 'RFI_LF', '31': 'RFI_HF', '32': 'RFO_HF',
    '30': 'GND', '15': 'GND', '33': 'GND',
}
part('U6', f'{PROJECT}:LR2021', 'LR2021IMLTRT', 'Package_DFN_QFN:QFN-32-1EP_5x5mm_P0.5mm_EP3.7x3.7mm_ThermalVias',
     150, 300, 0, LR_NETS, MPN='LR2021IMLTRT')
vfb('FB1', 25, 205, '+3V3', 'LR_VBAT')
vcap('C11', '100nF', 40, 205, 'LR_VBAT')
vcap('C12', '4.7uF', 55, 205, 'LR_VBAT')
vfb('FB2', 75, 205, 'VDCC1', 'VDCC')
vcap('C13', '1uF', 90, 205, 'VDCC1')
vcap('C14', '1uF', 105, 205, 'VDCC')
vfb('FB3', 25, 245, 'VPAX1', 'VPAX')
vcap('C15', '2.2uF', 40, 245, 'VPAX1')
vcap('C16', '2.2uF', 55, 245, 'VPAX')
vcap('C17', '1nF', 75, 245, 'VR_PA')
vind('L1', '2.2uH', 90, 245, 'LXA', 'LXB', fp='Inductor_SMD:L_0603_1608Metric', MPN='LQM18PN2R2MFRL', LCSC='C337910',
     Spec='SIMO inductor: DCR<0.5R, Isat>200mA, SRF>20MHz')
vres('R8', '120k', 30, 290, 'LR_VNTC', 'LR_NTC')
part('TH1', 'Device:Thermistor_NTC', '100k B4250', R0402, 42, 290, 0, {'1': 'LR_NTC', '2': 'GND'},
     MPN='NCP15WF104F03RC', LCSC='C77130')
part('Y1', 'Device:Crystal_GND24', '32MHz', 'Crystal:Crystal_SMD_2016-4Pin_2.0x1.6mm', 70, 290, 0,
     {'1': 'XTB', '3': 'XTA', '2': 'GND', '4': 'GND'}, Spec='32MHz, CL=10pF, +/-10ppm, ESR<60R (2016)')
part('PWR_FLAG_VBAT', 'power:PWR_FLAG', 'PWR_FLAG', '', 30, 330, 0, {}, flag_net='LR_VBAT')

# ---- RF: sub-GHz (915 MHz) path - Semtech LR2021 reference design values ---------
vind('L2', '12nH', 220, 200, 'VR_PA', 'RFO_LF', MPN='LQW15AN12NG00D', LCSC='C86128', **RFL)
vcap('C18', '47pF', 232, 200, 'VR_PA', **RFC)
hind('L3', '4.7nH', 255, 225, 'RFO_LF', 'LF_A', MPN='LQW15AN4N7B00D', LCSC='C98064', **RFL)
hcap('C19', '22pF', 290, 225, 'LF_A', 'LF_B', **RFC)
vcap('C20', '7.5pF', 310, 245, 'LF_B', **RFC)
hind('L4', '3.9nH', 330, 225, 'LF_B', 'LF_C', MPN='LQW15AN3N9B00D', LCSC='C98062', **RFL)
hcap('C21', '1.8pF', 330, 212, 'LF_B', 'LF_C', **RFC)
vcap('C22', '3.9pF', 350, 245, 'LF_C', **RFC)
hind('L5', '2.4nH', 370, 225, 'LF_C', 'ANT_LF', **RFL)
vcap('C23', '1.8pF', 390, 245, 'ANT_LF', **RFC)
vind('L6', '22nH', 402, 245, 'ANT_LF', 'GND', MPN='LQW15AN22NG00D', LCSC='C86129', **RFL)
part('D6', 'Device:D_TVS', 'ESD101-B1-02ELS', 'Diode_SMD:D_0402_1005Metric', 414, 245, 90, {'2': 'ANT_LF', '1': 'GND'},
     dnp=True, MPN='ESD101-B1-02ELS', Spec='Optional RF ESD, <=0.2pF, Vrwm>=5.5V')
part('J5', 'Connector:Conn_Coaxial', 'SMA 915MHz', 'Connector_Coaxial:SMA_Samtec_SMA-J-P-H-ST-EM1_EdgeMount', 445, 225, 0,
     {'1': 'ANT_LF', '2': 'GND'}, ref_pos=(3, -3), val_pos=(3, 3.5), MPN='SMA-J-P-H-ST-EM1', Spec='SMA female edge mount, 1.6mm PCB')
hcap('C24', '18pF', 370, 270, 'LF_RX', 'ANT_LF', **RFC)
vcap('C25', '2.2pF', 350, 288, 'LF_RX', **RFC)
hind('L7', '24nH', 320, 270, 'RFI_LF', 'LF_RX', MPN='LQW15AN24NG00D', LCSC='C167472', **RFL)

# ---- RF: 2.4 GHz path -----------------------------------------------------------
vind('L8', '18nH', 220, 310, 'VR_PA', 'RFO_HF', MPN='LQW15AN18NG00D', LCSC='C91622', **RFL)
vcap('C26', '47pF', 232, 310, 'VR_PA', **RFC)
hind('L9', '1.5nH', 255, 335, 'RFO_HF', 'HF_A', MPN='LQW15AN1N5B00D', LCSC='C18221', **RFL)
hcap('C27', '6.8pF', 290, 335, 'HF_A', 'HF_B', **RFC)
vcap('C28', '2.7pF', 310, 355, 'HF_B', **RFC)
hind('L10', '1.6nH', 330, 335, 'HF_B', 'HF_C', **RFL)
hcap('C29', '1.1pF', 330, 322, 'HF_B', 'HF_C', **RFC)
vcap('C30', '1.2pF', 350, 355, 'HF_C', **RFC)
hind('L11', '1.1nH', 370, 335, 'HF_C', 'ANT_HF', **RFL)
vcap('C31', '2.0pF', 390, 355, 'ANT_HF', **RFC)
vind('L12', 'DNP', 402, 355, 'ANT_HF', 'GND', dnp=True, **RFL)
part('D7', 'Device:D_TVS', 'ESD101-B1-02ELS', 'Diode_SMD:D_0402_1005Metric', 414, 355, 90, {'2': 'ANT_HF', '1': 'GND'},
     dnp=True, MPN='ESD101-B1-02ELS', Spec='Optional RF ESD, <=0.2pF, Vrwm>=5.5V')
part('J6', 'Connector:Conn_Coaxial', 'SMA 2.4GHz', 'Connector_Coaxial:SMA_Samtec_SMA-J-P-H-ST-EM1_EdgeMount', 445, 335, 0,
     {'1': 'ANT_HF', '2': 'GND'}, ref_pos=(3, -3), val_pos=(3, 3.5), MPN='SMA-J-P-H-ST-EM1', Spec='SMA female edge mount, 1.6mm PCB')
hcap('C32', '18pF', 330, 380, 'HF_RX', 'HF_C', **RFC)
vcap('C33', 'DNP', 310, 398, 'HF_RX', dnp=True, **RFC)
hind('L13', '2.4nH', 280, 380, 'RFI_HF', 'HF_RX', **RFL)

# ---- Mechanical / flags -----------------------------------------------------------
for i, (x, y) in enumerate([(525, 330), (540, 330)], 1):
    part(f'H{i}', 'Mechanical:MountingHole', 'MountingHole', 'MountingHole:MountingHole_3.2mm_M3', x, y)
part('PWR_FLAG_GND', 'power:PWR_FLAG', 'PWR_FLAG', '', 20, 150, 0, {}, flag_net='GND')
part('PWR_FLAG_5V', 'power:PWR_FLAG', 'PWR_FLAG', '', 200, 22, 0, {}, flag_net='+5V')
part('PWR_FLAG_VBUS', 'power:PWR_FLAG', 'PWR_FLAG', '', 100, 22, 0, {}, flag_net='VBUS')
part('PWR_FLAG_3V3EXT', 'power:PWR_FLAG', 'PWR_FLAG', '', 190, 120, 0, {}, flag_net='+3V3_EXT')

NOTES = [
    (15, 18, 'POWER INPUT: USB-C 5V / screw-terminal 5V -> Schottky OR -> AP7361C 1A LDO; external 3.3V and LDO 3.3V '
             'combined by two LM66100 ideal diodes (highest source wins, reverse-current blocked)'),
    (330, 18, 'ESP32-S3-WROOM-1-N16R8 (native USB on GPIO19/20; GPIO35-37 used by octal PSRAM)'),
    (15, 185, 'LR2021 core: SIMO DC-DC, 32MHz crystal with NTC compensation (Semtech reference design)'),
    (205, 185, 'RF: Semtech LR2021 reference design (switchless direct-tie). Top: 868/915MHz (PA_LF up to +22dBm). '
               'Bottom: 2.4GHz (PA_HF up to +12dBm). Keep layout tight, 50 ohm GCPW.'),
]
BOXES = [((10, 12), (330, 175)), ((325, 12), (585, 175)), ((10, 180), (200, 410)), ((200, 180), (510, 410))]


# ---------------------------------------------------------------- emit
def font(size=1.27, bold=False):
    f = [sym('font'), [sym('size'), size, size]]
    if bold:
        f.append([sym('bold'), sym('yes')])
    return f


def prop_node(name, value, x, y, angle=0, hide=False, justify=None):
    eff = [sym('effects'), font()]
    if justify:
        eff.append([sym('justify')] + [sym(j) for j in justify.split()])
    if hide:
        eff.append([sym('hide'), sym('yes')])
    return [sym('property'), name, value, [sym('at'), x, y, angle], eff]


def main():
    write_custom_lib()
    used = sorted({p['lib_id'] for p in parts} | set(POWER_NETS.values()) | {'power:PWR_FLAG'})
    body = []
    pwr_n = [0]
    errors = []

    def power_symbol(lib_id, net, x, y, rot):
        pwr_n[0] += 1
        ref = f'#PWR{pwr_n[0]:03d}'
        lib, name = lib_id.split(':')
        vprop = [pr for pr in find_all(flat_symbol(lib, name), 'property') if pr[1] == 'Value'][0]
        vx, vy = xform(float(find(vprop, 'at')[1]), float(find(vprop, 'at')[2]), rot)
        body.append([sym('symbol'), [sym('lib_id'), lib_id], [sym('at'), x, y, rot], [sym('unit'), 1],
                     [sym('exclude_from_sim'), sym('no')], [sym('in_bom'), sym('yes')], [sym('on_board'), sym('yes')],
                     [sym('dnp'), sym('no')], [sym('uuid'), uid('pwr')],
                     prop_node('Reference', ref, x, y, hide=True),
                     prop_node('Value', net, round(x + vx, 3), round(y + vy, 3)),
                     prop_node('Footprint', '', x, y, hide=True), prop_node('Datasheet', '', x, y, hide=True),
                     [sym('pin'), '1', [sym('uuid'), uid('pp')]],
                     [sym('instances'), [sym('project'), PROJECT, [sym('path'), '/' + ROOT_UUID,
                                                                   [sym('reference'), ref], [sym('unit'), 1]]]]])

    def attach(net, x, y, d):
        """Wire stub from (x,y) in direction d, ending in a label or power symbol."""
        ex, ey = round(x + d[0] * STUB, 3), round(y + d[1] * STUB, 3)
        body.append([sym('wire'), [sym('pts'), [sym('xy'), x, y], [sym('xy'), ex, ey]],
                     [sym('stroke'), [sym('width'), 0], [sym('type'), sym('default')]], [sym('uuid'), uid('w')]])
        if net in POWER_NETS:
            if net == 'GND':
                rot = {(0, 1): 0, (0, -1): 180, (1, 0): 90, (-1, 0): 270}[d]
            else:
                rot = {(0, -1): 0, (0, 1): 180, (-1, 0): 90, (1, 0): 270}[d]
            power_symbol(POWER_NETS[net], net, ex, ey, rot)
        else:
            ang, just = {(1, 0): (0, 'left bottom'), (-1, 0): (180, 'right bottom'),
                         (0, -1): (90, 'left bottom'), (0, 1): (270, 'right bottom')}[d]
            body.append([sym('label'), net, [sym('at'), ex, ey, ang],
                         [sym('fields_autoplaced'), sym('yes')],
                         [sym('effects'), font(), [sym('justify')] + [sym(j) for j in just.split()]],
                         [sym('uuid'), uid('l')]])

    for p in parts:
        lib_id = p['lib_id']
        pins = symbol_pins(lib_id)
        X, Y, rot = p['x'], p['y'], p['rot']
        is_flag = lib_id == 'power:PWR_FLAG'
        u = uid('sym')
        # Pin positions, grouped so stacked pins only get one stub.
        seen = {}
        for pin in pins:
            ox, oy = xform(pin['x'], pin['y'], rot)
            pos = (round(X + ox, 3), round(Y + oy, 3))
            if is_flag:
                continue
            net = p['nets'].get(pin['num'])
            if net is None:
                errors.append(f"{p['ref']} pin {pin['num']} ({pin['name']}) has no net")
                continue
            if pos in seen:
                if seen[pos] != net:
                    errors.append(f"{p['ref']} stacked pin {pin['num']} net mismatch")
                continue
            seen[pos] = net
            if net == NC:
                body.append([sym('no_connect'), [sym('at'), pos[0], pos[1]], [sym('uuid'), uid('nc')]])
            else:
                attach(net, pos[0], pos[1], outward(pin['a'], rot))
        for num in p['nets']:
            if num not in {pin['num'] for pin in pins}:
                errors.append(f"{p['ref']} has net for unknown pin {num}")
        if is_flag:
            net = p['fields'].pop('flag_net')
            if net in POWER_NETS:
                power_symbol(POWER_NETS[net], net, X, Y, 180 if net == 'GND' else 0)
            else:
                body.append([sym('label'), net, [sym('at'), X, Y, 0], [sym('fields_autoplaced'), sym('yes')],
                             [sym('effects'), font(), [sym('justify'), sym('left'), sym('bottom')]], [sym('uuid'), uid('l')]])
            pwr_n[0] += 1
            ref = f'#FLG{pwr_n[0]:03d}'
        else:
            ref = p['ref']
        # Field placement.
        xs = [xform(pn['x'], pn['y'], rot)[0] for pn in pins] or [0]
        ys = [xform(pn['x'], pn['y'], rot)[1] for pn in pins] or [0]
        # Field angles are stored in the symbol's local frame, so undo the symbol rotation.
        fa = rot % 180
        two_pin_vertical = len(pins) == 2 and max(xs) == min(xs)
        if is_flag:
            rp, vp, vj = (X, Y - 6), (X + 1.27, Y - 3.5), 'left'
        elif two_pin_vertical:
            rp, vp, vj = (X + 2.54, Y - 1.27), (X + 2.54, Y + 1.27), 'left'
        elif len(pins) <= 2:
            rp, vp, vj = (X, Y - 3.2), (X, Y + 3.8), None
        else:
            rp, vp, vj = (X + min(xs), Y + min(ys) - 2), (X + min(xs), Y + max(ys) + 3), 'left'
        if p['ref_pos']:
            rp = (X + p['ref_pos'][0], Y + p['ref_pos'][1])
        if p['val_pos']:
            vp, vj = (X + p['val_pos'][0], Y + p['val_pos'][1]), 'left'
        if vj and fa:
            vj = 'right' if rot == 90 else 'left'
        props = [prop_node('Reference', ref, rp[0], rp[1], angle=fa, hide=is_flag, justify=vj),
                 prop_node('Value', p['value'], vp[0], vp[1], angle=fa, justify=vj, hide=False),
                 prop_node('Footprint', p['fp'], X, Y, hide=True),
                 prop_node('Datasheet', '', X, Y, hide=True)]
        for k, v in p['fields'].items():
            props.append(prop_node(k, v, X, Y, hide=True))
        node = [sym('symbol'), [sym('lib_id'), lib_id], [sym('at'), X, Y, rot], [sym('unit'), 1],
                [sym('exclude_from_sim'), sym('no')],
                [sym('in_bom'), sym('no' if is_flag or lib_id.startswith('Mechanical:') else 'yes')],
                [sym('on_board'), sym('no' if is_flag else 'yes')], [sym('dnp'), sym('yes' if p['dnp'] else 'no')],
                [sym('uuid'), u]] + props
        for pin in pins:
            node.append([sym('pin'), pin['num'], [sym('uuid'), uid('pin')]])
        node.append([sym('instances'), [sym('project'), PROJECT, [sym('path'), '/' + ROOT_UUID,
                                                                  [sym('reference'), ref], [sym('unit'), 1]]]])
        body.append(node)

    for x, y, text in NOTES:
        body.append([sym('text'), text, [sym('exclude_from_sim'), sym('no')], [sym('at'), x, y, 0],
                     [sym('effects'), font(2.0, True), [sym('justify'), sym('left'), sym('bottom')]], [sym('uuid'), uid('t')]])
    for (x1, y1), (x2, y2) in BOXES:
        body.append([sym('rectangle'), [sym('start'), x1, y1], [sym('end'), x2, y2],
                     [sym('stroke'), [sym('width'), 0.3], [sym('type'), sym('dash')]],
                     [sym('fill'), [sym('type'), sym('none')]], [sym('uuid'), uid('r')]])

    if errors:
        raise SystemExit('\n'.join(errors))

    sch = [sym('kicad_sch'), [sym('version'), 20250114], [sym('generator'), 'eeschema'], [sym('generator_version'), '9.0'],
           [sym('uuid'), ROOT_UUID], [sym('paper'), 'A2'],
           [sym('title_block'), [sym('title'), 'LR2021 + ESP32-S3 LoRa Plus board'], [sym('date'), '2026-10-02'],
            [sym('rev'), '1.0'], [sym('comment'), 1, 'Generated by scripts/gen_schematic.py'],
            [sym('comment'), 2, 'RF matching per Semtech LR2021 reference design (868/915MHz + 2.4GHz)']],
           [sym('lib_symbols')] + [embedded(l) for l in used]] + body + [
        [sym('sheet_instances'), [sym('path'), '/', [sym('page'), '1']]], [sym('embedded_fonts'), sym('no')]]
    out = os.path.join(PROJ_DIR, f'{PROJECT}.kicad_sch')
    with open(out, 'w') as f:
        f.write(dumps(sch) + '\n')
    print(f'wrote {out}: {len([p for p in parts if not p["lib_id"].startswith("power:")])} parts')


if __name__ == '__main__':
    main()
