#!/usr/bin/env python3
"""Render the enclosure with and without the board (PyVista, off-screen).

Needs: gen_enclosure.py run first (build/*_assembled.stl), the board as GLB
(kicad-cli pcb export glb --subst-models -o build/board.glb ../lr2021_esp32s3.kicad_pcb)
and pyvista. Run under xvfb-run on a headless machine. Writes ../docs/enclosure/*.png.
"""
import os

import numpy as np
import pyvista as pv

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), 'docs', 'enclosure')
BASE_C, LID_C = (0.22, 0.24, 0.28), (0.86, 0.87, 0.89)
CENTER = np.array([131.0, -123.5, 4.0])          # STEP frame, mm


def to_gltf(mesh, dz=0.0):
    """STEP frame (mm, Z up) -> glTF frame of the board GLB (m, Y up, Z = KiCad Y)."""
    m = mesh.copy()
    p = m.points.copy()
    m.points = np.c_[p[:, 0], p[:, 2] + dz, -p[:, 1]] / 1000.0
    return m


def cam(view):
    c = CENTER
    # STEP Y = -KiCad Y, so the board's front edge (KiCad y = 147) faces -Y
    d = {'front_left': (-95, -125, 85), 'back_right': (100, 125, 80), 'top': (0, 0, 190),
         'below': (-80, -100, -120), 'front': (0, -150, 30), 'right': (160, 0, 25),
         'left': (-160, -20, 30)}[view]
    pos = c + np.array(d)
    g = lambda v: (v[0] / 1000, v[2] / 1000, -v[1] / 1000)  # noqa: E731
    up = (0, 0, 1) if view != 'top' else (0, 1, 0)
    return [g(pos), g(c), (up[0], up[2], -up[1])]


def shot(name, view, base=None, lid=None, board=None, zoom=1.0):
    pl = pv.Plotter(off_screen=True, window_size=(1600, 1150))
    pl.set_background('#eef0f4', top='#ffffff')
    if board is not None:
        pl.import_gltf(os.path.join(HERE, 'build', 'board.glb'))
        if board:
            for a in pl.renderer.actors.values():
                a.SetPosition(0, board / 1000, 0)
    for mesh, color, dz in ((base, BASE_C, 0), (lid, LID_C, None)):
        if mesh is None:
            continue
        m, off = mesh if isinstance(mesh, tuple) else (mesh, 0)
        pl.add_mesh(to_gltf(m, off), color=color, smooth_shading=False, specular=0.25, specular_power=20)
    pl.enable_lightkit()
    pl.camera_position = cam(view)
    pl.camera.zoom(zoom)
    os.makedirs(OUT, exist_ok=True)
    pl.screenshot(os.path.join(OUT, name))
    pl.close()
    print('wrote', name)


def main():
    base = pv.read(os.path.join(HERE, 'build', 'base_assembled.stl'))
    lid = pv.read(os.path.join(HERE, 'build', 'lid_assembled.stl'))
    shot('01_closed_front_left.png', 'front_left', base, lid, board=0.0)
    shot('02_closed_back_right.png', 'back_right', base, lid, board=0.0)
    shot('03_exploded.png', 'front_left', base, (lid, 34), board=17.0, zoom=0.85)
    shot('04_base_with_board.png', 'front_left', base, None, board=0.0)
    shot('05_base_only.png', 'front_left', base)
    shot('06_lid_top.png', 'front_left', None, lid)
    shot('07_lid_underside.png', 'below', None, lid)
    shot('08_closed_no_board.png', 'front_left', base, lid)
    shot('09_exploded_no_board.png', 'front_left', base, (lid, 26), zoom=0.9)
    shot('10_top_view.png', 'top', base, lid, board=0.0)
    shot('11_usb_side.png', 'left', base, lid, board=0.0, zoom=1.3)
    shot('12_sma_side.png', 'right', base, lid, board=0.0, zoom=1.3)


if __name__ == '__main__':
    main()
