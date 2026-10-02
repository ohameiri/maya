#!/usr/bin/env python3
"""Write the KiCad project file (ERC settings, net classes, JLCPCB 4-layer rules)."""
import json
import os
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ_DIR = os.path.dirname(HERE)
PROJECT = 'lr2021_esp32s3'
ROOT_UUID = str(uuid.uuid5(uuid.UUID('6f1c2a8e-35a1-4c1e-9d0e-2b5a3c4d1e01'), 'root'))

# KiCad's default ERC pin conflict matrix. Order: input, output, bidirectional, tri-state,
# passive, free, unspecified, power_in, power_out, open_collector, open_emitter, no_connect.
PIN_MAP = [
    [0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 2],
    [0, 2, 0, 1, 0, 0, 1, 0, 2, 2, 2, 2],
    [0, 0, 0, 0, 0, 0, 1, 0, 1, 0, 1, 2],
    [0, 1, 0, 0, 0, 0, 1, 1, 2, 1, 1, 2],
    [0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 2],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 2],
    [1, 1, 1, 1, 1, 0, 1, 1, 1, 1, 1, 2],
    [0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0, 2],
    [0, 2, 1, 2, 0, 0, 1, 0, 2, 2, 2, 2],
    [0, 2, 0, 1, 0, 0, 1, 0, 2, 0, 0, 2],
    [0, 2, 1, 1, 0, 0, 1, 0, 2, 0, 0, 2],
    [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2],
]
# The two LM66100 ideal diodes deliberately drive the same +3V3 rail (diode-OR),
# so power_out <-> power_out is a warning instead of an error.
PIN_MAP[8][8] = 1

RULE_SEVERITIES = {
    "bus_definition_conflict": "error", "bus_entry_needed": "error", "bus_to_bus_conflict": "error",
    "bus_to_net_conflict": "error", "different_unit_footprint": "error", "different_unit_net": "error",
    "duplicate_reference": "error", "duplicate_sheet_names": "error", "endpoint_off_grid": "warning",
    "extra_units": "error", "footprint_filter": "ignore", "footprint_link_issues": "warning",
    "four_way_junction": "ignore", "global_label_dangling": "warning", "hier_label_mismatch": "error",
    "label_dangling": "error", "label_multiple_wires": "warning", "lib_symbol_issues": "warning",
    "lib_symbol_mismatch": "warning", "missing_bidi_pin": "warning", "missing_input_pin": "warning",
    "missing_power_pin": "error", "missing_unit": "warning", "multiple_net_names": "warning",
    "net_not_bus_member": "warning", "no_connect_connected": "warning", "no_connect_dangling": "warning",
    "pin_not_connected": "error", "pin_not_driven": "error", "pin_to_pin": "warning",
    "power_pin_not_driven": "error", "same_local_global_label": "warning", "similar_label_and_power": "warning",
    "similar_labels": "warning", "similar_power": "warning", "simulation_model_issue": "ignore",
    "single_global_label": "ignore", "unannotated": "error", "unconnected_wire_endpoint": "warning",
    "unit_value_mismatch": "error", "unresolved_variable": "error", "wire_dangling": "error",
}

RF_NETS = ['RFO_LF', 'LF_A', 'LF_B', 'LF_C', 'ANT_LF', 'LF_RX', 'RFI_LF',
           'RFO_HF', 'HF_A', 'HF_B', 'HF_C', 'ANT_HF', 'HF_RX', 'RFI_HF']
POWER_NETS = ['+5V', 'VBUS', '+5V_EXT', '+3V3', '+3V3_LDO', '+3V3_EXT', 'LR_VBAT', 'VR_PA',
              'VPAX', 'VPAX1', 'VDCC', 'VDCC1', 'LXA', 'LXB']


def netclass(name, track, clearance, via_d=0.6, via_drill=0.3, priority=0, dp_w=0.2, dp_gap=0.2):
    return {"bus_width": 12, "clearance": clearance, "diff_pair_gap": dp_gap, "diff_pair_via_gap": 0.25,
            "diff_pair_width": dp_w, "line_style": 0, "microvia_diameter": 0.3, "microvia_drill": 0.1,
            "name": name, "pcb_color": "rgba(0, 0, 0, 0.000)", "priority": priority,
            "schematic_color": "rgba(0, 0, 0, 0.000)", "track_width": track, "via_diameter": via_d,
            "via_drill": via_drill, "wire_width": 6}


def patterns():
    out = []
    for n in RF_NETS:
        out += [{"netclass": "RF_50R", "pattern": n}, {"netclass": "RF_50R", "pattern": "/" + n}]
    for n in POWER_NETS:
        out += [{"netclass": "Power", "pattern": n}, {"netclass": "Power", "pattern": "/" + n}]
    out += [{"netclass": "USB_90R", "pattern": "/USB_D?"}]
    return out


def main():
    pro = {
        "board": {
            "3dviewports": [],
            "design_settings": {
                "defaults": {
                    "board_outline_line_width": 0.05, "copper_line_width": 0.2, "copper_text_size_h": 1.5,
                    "copper_text_size_v": 1.5, "copper_text_thickness": 0.3, "courtyard_line_width": 0.05,
                    "fab_line_width": 0.1, "fab_text_size_h": 1.0, "fab_text_size_v": 1.0, "fab_text_thickness": 0.15,
                    "other_line_width": 0.1, "silk_line_width": 0.12, "silk_text_size_h": 1.0,
                    "silk_text_size_v": 1.0, "silk_text_thickness": 0.15,
                    "zones": {"45_degree_only": False, "min_clearance": 0.2},
                },
                "diff_pair_dimensions": [{"gap": 0.15, "via_gap": 0.25, "width": 0.2}],
                "drc_exclusions": [],
                "rule_severities": {"silk_overlap": "warning", "silk_over_copper": "warning",
                                    "lib_footprint_issues": "ignore", "lib_footprint_mismatch": "ignore",
                                    "text_height": "warning", "text_thickness": "warning"},
                # JLCPCB standard 4-layer capability with margin.
                "rules": {
                    "allow_blind_buried_vias": False, "allow_microvias": False, "max_error": 0.005,
                    "min_clearance": 0.1, "min_connection": 0.0, "min_copper_edge_clearance": 0.3,
                    "min_groove_width": 0.0, "min_hole_clearance": 0.25, "min_hole_to_hole": 0.25,
                    "min_microvia_diameter": 0.2, "min_microvia_drill": 0.1, "min_resolved_spokes": 1,
                    "min_silk_clearance": 0.0, "min_text_height": 0.8, "min_text_thickness": 0.08,
                    "min_through_hole_diameter": 0.2, "min_track_width": 0.1, "min_via_annular_width": 0.1,
                    "min_via_diameter": 0.45, "solder_mask_to_copper_clearance": 0.0,
                    "use_height_for_length_calcs": True,
                },
                "track_widths": [0.0, 0.15, 0.2, 0.25, 0.38, 0.5, 0.8, 1.0],
                "via_dimensions": [{"diameter": 0.0, "drill": 0.0}, {"diameter": 0.45, "drill": 0.25},
                                   {"diameter": 0.6, "drill": 0.3}, {"diameter": 0.8, "drill": 0.4}],
                "zones_allow_external_fillets": False,
            },
            "ipc2581": {"dist": "", "distpn": "", "internal_id": "", "mfg": "", "mpn": ""},
            "layer_pairs": [], "layer_presets": [], "viewports": [],
        },
        "boards": [],
        "cvpcb": {"equivalence_files": []},
        "erc": {"erc_exclusions": [], "meta": {"version": 0}, "pin_map": PIN_MAP, "rule_severities": RULE_SEVERITIES},
        "libraries": {"pinned_footprint_libs": [], "pinned_symbol_libs": []},
        "meta": {"filename": f"{PROJECT}.kicad_pro", "version": 3},
        "net_settings": {
            "classes": [
                netclass("Default", 0.2, 0.15, priority=2147483647),
                netclass("Power", 0.5, 0.2, 0.8, 0.4, priority=1),
                # 50 ohm grounded coplanar waveguide on L1 over the L2 ground (JLC04161H-7628,
                # 0.2104mm prepreg, er 4.4): 0.38mm track, 0.2mm gap -> ~49.7 ohm.
                netclass("RF_50R", 0.38, 0.2, 0.6, 0.3, priority=0),
                netclass("USB_90R", 0.2, 0.15, priority=2, dp_w=0.2, dp_gap=0.15),
            ],
            "meta": {"version": 4}, "net_colors": None, "netclass_assignments": None,
            "netclass_patterns": patterns(),
        },
        "pcbnew": {"last_paths": {}, "page_layout_descr_file": ""},
        "schematic": {
            "annotate_start_num": 0, "bom_export_filename": "${PROJECTNAME}.csv", "connection_grid_size": 50.0,
            "drawing": {"default_line_thickness": 6.0, "default_text_size": 50.0, "field_names": [],
                        "intersheets_ref_own_page": False, "intersheets_ref_prefix": "", "intersheets_ref_short": False,
                        "intersheets_ref_show": False, "intersheets_ref_suffix": "", "junction_size_choice": 3,
                        "label_size_ratio": 0.375, "operating_point_overlay_i_precision": 3,
                        "operating_point_overlay_i_range": "~A", "operating_point_overlay_v_precision": 3,
                        "operating_point_overlay_v_range": "~V", "overbar_offset_ratio": 1.23,
                        "pin_symbol_size": 25.0, "text_offset_ratio": 0.15},
            "legacy_lib_dir": "", "legacy_lib_list": [], "meta": {"version": 1}, "net_format_name": "",
            "page_layout_descr_file": "", "plot_directory": "", "space_save_all_events": True,
            "spice_current_sheet_as_root": False, "spice_external_command": "spice \"%I\"",
            "spice_model_current_sheet_as_root": True, "spice_save_all_currents": False,
            "spice_save_all_dissipations": False, "spice_save_all_voltages": False,
            "subpart_first_id": 65, "subpart_id_separator": 0,
        },
        "sheets": [[ROOT_UUID, "Root"]],
        "text_variables": {},
    }
    with open(os.path.join(PROJ_DIR, f'{PROJECT}.kicad_pro'), 'w') as f:
        json.dump(pro, f, indent=2)
        f.write('\n')
    print('wrote project file')


if __name__ == '__main__':
    main()
