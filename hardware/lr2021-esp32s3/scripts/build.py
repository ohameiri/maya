#!/usr/bin/python3
"""Rebuild the whole design: project -> schematic -> PCB -> autoroute -> checks -> fab outputs.

Freerouting is not deterministic, so routing is retried from the same pre-route
board until DRC reports no unconnected items and no errors.

Usage: /usr/bin/python3 build.py [path/to/freerouting-1.9.0.jar]
"""
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
NAME = 'lr2021_esp32s3'
PCB = os.path.join(PROJ, f'{NAME}.kicad_pcb')
SCH = os.path.join(PROJ, f'{NAME}.kicad_sch')
PY = '/usr/bin/python3'
ATTEMPTS = 6


def run(*cmd, **kw):
    print('>', ' '.join(cmd), flush=True)
    return subprocess.run(cmd, check=True, cwd=HERE, **kw)


def drc():
    rpt = '/tmp/claude-0/drc_build.rpt'
    subprocess.run(['kicad-cli', 'pcb', 'drc', '--schematic-parity', '--severity-all', '-o', rpt, PCB],
                   check=True, capture_output=True)
    text = open(rpt).read()
    unconnected = int(re.search(r'Found (\d+) unconnected', text).group(1))
    errors = len(re.findall(r'; error', text))
    parity = int(re.search(r'Found (\d+) Footprint errors', text).group(1))
    return unconnected, errors, parity, text


def main():
    jar = sys.argv[1:] or []
    run(PY, 'gen_project.py')
    run(PY, 'gen_schematic.py')
    erc = subprocess.run(['kicad-cli', 'sch', 'erc', '--severity-error', '--exit-code-violations',
                          '-o', '/tmp/claude-0/erc_build.rpt', SCH], capture_output=True)
    if erc.returncode != 0:
        raise SystemExit('ERC errors, see /tmp/claude-0/erc_build.rpt')
    run(PY, 'gen_pcb.py')
    preroute = PCB + '.preroute'
    shutil.copy(PCB, preroute)
    for attempt in range(1, ATTEMPTS + 1):
        shutil.copy(preroute, PCB)
        run(PY, 'route.py', *jar, env={**os.environ, 'FR_PASSES': '80'})
        unconnected, errors, parity, _ = drc()
        print(f'attempt {attempt}: unconnected={unconnected} errors={errors} parity={parity}', flush=True)
        if unconnected == 0 and errors == 0 and parity == 0:
            break
    else:
        raise SystemExit('routing did not converge; see /tmp/claude-0/drc_build.rpt')
    os.remove(preroute)
    run(PY, 'export_fab.py')


if __name__ == '__main__':
    main()
