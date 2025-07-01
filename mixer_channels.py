OUTPUT_TABS = [
    ("AN1", "AN2"),
    ("PH3", "PH4"),
    ("AS1", "AS2"),
    ("ADAT3", "ADAT4"),
    ("ADAT5", "ADAT6"),
    ("ADAT7", "ADAT8"),
]

GROUP_ORDER = ["Mic", "Line", "ADAT", "PCM"]

# Canonical inputs for each group
GROUP_INPUTS = {
    "Mic":    ("AN1", "AN2"),
    "Line":   ("IN3", "IN4"),
    "ADAT":   ( # ADAT sources (each row in your grid is a pair)
        ("AS1", "AS2"), ("ADAT3", "ADAT4"), ("ADAT5", "ADAT6"), ("ADAT7", "ADAT8")
    ),
    "PCM":    ("AN1", "AN2"),  # Will override for each tab
}

# Canonical mixer channel pairs, based on your image/table:
CANONICAL_PAIRS = {
    ("AN1", "AN2"): {
        "Mic":  [("Mic-AN1-AN1", "Mic-AN2-AN2")],
        "Line": [("Line-IN3-AN1", "Line-IN4-AN2")],
        "ADAT": [
            ("Line-AS1-AN1", "Line-AS2-AN2"),
            ("Line-ADAT3-AN1", "Line-ADAT4-AN2"),
            ("Line-ADAT5-AN1", "Line-ADAT6-AN2"),
            ("Line-ADAT7-AN1", "Line-ADAT8-AN2"),
        ],
        "PCM":  [("PCM-AN1-AN1", "PCM-AN2-AN2")],
    },
    ("PH3", "PH4"): {
        "Mic":  [("Mic-AN1-PH3", "Mic-AN2-PH4")],
        "Line": [("Line-IN3-PH3", "Line-IN4-PH4")],
        "ADAT": [
            ("Line-AS1-PH3", "Line-AS2-PH4"),
            ("Line-ADAT3-PH3", "Line-ADAT4-PH4"),
            ("Line-ADAT5-PH3", "Line-ADAT6-PH4"),
            ("Line-ADAT7-PH3", "Line-ADAT8-PH4"),
        ],
        "PCM":  [("PCM-PH3-PH3", "PCM-PH4-PH4")],
    },
    ("AS1", "AS2"): {
        "Mic":  [("Mic-AN1-AS1", "Mic-AN2-AS2")],
        "Line": [("Line-IN3-AS1", "Line-IN4-AS2")],
        "ADAT": [
            ("Line-AS1-AS1", "Line-AS2-AS2"),
            ("Line-ADAT3-AS1", "Line-ADAT4-AS2"),
            ("Line-ADAT5-AS1", "Line-ADAT6-AS2"),
            ("Line-ADAT7-AS1", "Line-ADAT8-AS2"),
        ],
        "PCM":  [("PCM-AS1-AS1", "PCM-AS2-AS2")],
    },
    ("ADAT3", "ADAT4"): {
        "Mic":  [("Mic-AN1-ADAT3", "Mic-AN2-ADAT4")],
        "Line": [("Line-IN3-ADAT3", "Line-IN4-ADAT4")],
        "ADAT": [
            ("Line-AS1-ADAT3", "Line-AS2-ADAT4"),
            ("Line-ADAT3-ADAT3", "Line-ADAT4-ADAT4"),
            ("Line-ADAT5-ADAT3", "Line-ADAT6-ADAT4"),
            ("Line-ADAT7-ADAT3", "Line-ADAT8-ADAT4"),
        ],
        "PCM":  [("PCM-ADAT3-ADAT3", "PCM-ADAT4-ADAT4")],
    },
    ("ADAT5", "ADAT6"): {
        "Mic":  [("Mic-AN1-ADAT5", "Mic-AN2-ADAT6")],
        "Line": [("Line-IN3-ADAT5", "Line-IN4-ADAT6")],
        "ADAT": [
            ("Line-AS1-ADAT5", "Line-AS2-ADAT6"),
            ("Line-ADAT3-ADAT5", "Line-ADAT4-ADAT6"),
            ("Line-ADAT5-ADAT5", "Line-ADAT6-ADAT6"),
            ("Line-ADAT7-ADAT5", "Line-ADAT8-ADAT6"),
        ],
        "PCM":  [("PCM-ADAT5-ADAT5", "PCM-ADAT6-ADAT6")],
    },
    ("ADAT7", "ADAT8"): {
        "Mic":  [("Mic-AN1-ADAT7", "Mic-AN2-ADAT8")],
        "Line": [("Line-IN3-ADAT7", "Line-IN4-ADAT8")],
        "ADAT": [
            ("Line-AS1-ADAT7", "Line-AS2-ADAT8"),
            ("Line-ADAT3-ADAT7", "Line-ADAT4-ADAT8"),
            ("Line-ADAT5-ADAT7", "Line-ADAT6-ADAT8"),
            ("Line-ADAT7-ADAT7", "Line-ADAT8-ADAT8"),
        ],
        "PCM":  [("PCM-ADAT7-ADAT7", "PCM-ADAT8-ADAT8")],
    },
}

def build_output_map(alsa_backend, card_index=1):
    """
    Build the canonical output map: only pairs in CANONICAL_PAIRS will be used.
    If an ALSA control is missing (e.g. not present for your hardware), that strip is skipped.
    """
    all_controls = set(alsa_backend.get_all_controls(card_index))
    output_map = {}
    for tab_pair, group_dict in CANONICAL_PAIRS.items():
        group_map = {}
        for group, pairlist in group_dict.items():
            valid_pairs = []
            for l_name, r_name in pairlist:
                if l_name in all_controls and r_name in all_controls:
                    valid_pairs.append((l_name, r_name))
            if valid_pairs:
                group_map[group] = valid_pairs
        output_map[tab_pair] = group_map
    func_map = {}  # Placeholder for function controls
    return output_map, func_map
