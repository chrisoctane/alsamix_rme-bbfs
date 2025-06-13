# alsa_backend.py
import alsaaudio
import re

def list_cards():
    """Return ALSA card index/name list."""
    return [(i, alsaaudio.card_name(i)) for i in range(alsaaudio.card_indexes())]

def list_mixer_controls(cardindex=1):
    """Return list of all mixer controls for the card."""
    return alsaaudio.mixers(cardindex=cardindex)

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

# You can add get/set_pan and other helpers as needed!
