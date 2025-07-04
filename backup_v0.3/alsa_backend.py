# alsa_backend.py
import alsaaudio
import re

def list_cards():
    """Return ALSA card index/name list."""
    return [(i, alsaaudio.card_name(i)) for i in range(alsaaudio.card_indexes())]

def list_mixer_controls(cardindex=1):
    """Return list of all mixer controls for the card."""
    return alsaaudio.mixers(cardindex=cardindex)

def get_all_controls(card_index=1):
    """
    Returns a list of all control names for the given ALSA card.
    """
    try:
        mixer = alsaaudio.Mixer(cardindex=card_index)
        controls = mixer.list()
        print("ALSA controls detected:", controls)
        return controls
    except Exception:
        # Fallback: scan all controls (more robust for complex devices)
        controls = []
        try:
            cards = alsaaudio.cards()
            if card_index < len(cards):
                cardname = cards[card_index]
                for ctl in alsaaudio.mixers(cardindex=card_index):
                    controls.append(ctl)
        except Exception:
            pass
        print("ALSA controls detected (fallback):", controls)
        return controls


def parse_control_name(name):
    """
    Return (src, dst) from an ALSA control name like 'PCM-AN1-AN2'.
    For 'Main-Out AN1', returns ('Main-Out', 'AN1').
    """
    # Example: PCM-AN1-AN2, Main-Out AN1, etc.
    match = re.match(r"(PCM|Line|Mic|Main-Out|IEC958|.+?)-?([A-Z0-9]+)?-?([A-Z0-9]+)?", name)
    if match:
        parts = [p for p in match.groups() if p]
        if len(parts) == 3:
            return (parts[1], parts[2])
        elif len(parts) == 2:
            return (parts[0], parts[1])
    return (None, None)

def all_routes(cardindex=1):
    """
    Returns a dict mapping each output (destination) to a list of (control_name, source) tuples.
    For example: { 'AN1': [('PCM-AN1-AN1', 'AN1'), ...], 'ADAT3': ... }
    """
    controls = list_mixer_controls(cardindex)
    routing = {}
    for ctl in controls:
        src, dst = parse_control_name(ctl)
        if dst:
            routing.setdefault(dst, []).append( (ctl, src) )
    return routing

def get_volume(control, cardindex=1):
    """Return int 0-100."""
    try:
        return alsaaudio.Mixer(control=control, cardindex=cardindex).getvolume()[0]
    except Exception:
        return 0

def set_volume(control, value, cardindex=1):
    """Set int 0-100."""
    try:
        alsaaudio.Mixer(control=control, cardindex=cardindex).setvolume(value)
    except Exception:
        pass

def get_mixer(control, cardindex=1):
    """Get ALSA mixer object for a control."""
    try:
        return alsaaudio.Mixer(control=control, cardindex=cardindex)
    except Exception:
        return None

def set_crosspoint_volume(chan_L, chan_R, main_L, main_R, pan_val, linked):
    """
    Sets ALSA volume for main and cross controls based on pan position.
    If linked: 'pan_val' is a single value (-100..0..+100) for balance, write to main_L/R only.
    If unlinked: 'pan_val' is (panL, panR), write to all four (main/cross).
    """
    if linked:
        # Classic balance: -100 = left only, +100 = right only
        left_gain = 100 if pan_val <= 0 else int(100 * (1 - pan_val / 100))
        right_gain = 100 if pan_val >= 0 else int(100 * (1 + pan_val / 100))
        set_volume(main_L, left_gain)
        set_volume(main_R, right_gain)
        # Crosspoints set to zero
        set_volume(chan_L, 0)
        set_volume(chan_R, 0)
    else:
        # Full mono panning: panL/R are -100..0..+100 for each side
        panL, panR = pan_val
        # Left input panned to both outs
        set_volume(main_L, 100 if panL <= 0 else int(100 * (1 - panL / 100)))
        set_volume(chan_R, 100 if panL >= 0 else int(100 * (panL / 100)))
        # Right input panned to both outs
        set_volume(main_R, 100 if panR >= 0 else int(100 * (1 + panR / 100)))
        set_volume(chan_L, 100 if panR <= 0 else int(100 * (-panR / 100)))

# You can add get/set_pan and other helpers as needed!
