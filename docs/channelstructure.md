# Babyface Pro FS — Channel Layout and Routing Guide

This document defines the **canonical channel layout** for the main mixer and patchbay, covering:
- Stereo input pairs (with grouping and naming conventions)
- Function (non-routing) controls per channel
- Output channels (including special digital outs)
- The logic for pairing, grouping, and displaying channels in the UI

**This document is the single source of truth for UI design, channel pairing, and mixer logic.**

---

## 1. Stereo Input Pairs (for Main Out AN1/AN2)

### MIC Group
- **Mic-AN1-AN1** (L) + **Mic-AN2-AN2** (R)

### LINE Group
- **Line-IN3-AN1** (L) + **Line-IN4-AN2** (R)

### ADAT Group
- **Line-AS1-AN1** (L) + **Line-AS2-AN2** (R)  *(ADAT 1/2 — appears first in ADAT group)*
- **Line-ADAT3-AN1** (L) + **Line-ADAT4-AN2** (R)
- **Line-ADAT5-AN1** (L) + **Line-ADAT6-AN2** (R)
- **Line-ADAT7-AN1** (L) + **Line-ADAT8-AN2** (R)

### PCM Group
- **PCM-AN1-AN1** (L) + **PCM-AN2-AN2** (R)
- **PCM-PH3-AN1** (L) + **PCM-PH4-AN2** (R)  *(System/PCM audio → Headphones PH3/PH4 → Main Out AN1/AN2)*
- **PCM-AS1-AN1** (L) + **PCM-AS2-AN2** (R)
- **PCM-ADAT3-AN1** (L) + **PCM-ADAT4-AN2** (R)
- **PCM-ADAT5-AN1** (L) + **PCM-ADAT6-AN2** (R)
- **PCM-ADAT7-AN1** (L) + **PCM-ADAT8-AN2** (R)

---

## 2. Function Controls (Non-Routed, Per-Input Channel)

Function controls are **hardware-level settings** (not audio sources/faders) but are essential for correct operation and should be **displayed above or with the related input**.

### Mic Inputs
- `Mic-AN1 Gain` — Gain for Mic 1 (*rotary/slider*)
- `Mic-AN1 PAD` — Pad toggle for Mic 1
- `Mic-AN1 48V` — Phantom power toggle for Mic 1
- `Mic-AN2 Gain`
- `Mic-AN2 PAD`
- `Mic-AN2 48V`

### Line Inputs
- `Line-IN3 Gain` — Gain for Line In 3
- `Line-IN3 Sens.` — Sensitivity/+4dB/-10dBV for Line In 3
- `Line-IN4 Gain`
- `Line-IN4 Sens.`

### Global/Digital/Other
- `IEC958 Emphasis`
- `IEC958 Pro Mask`
- `IEC958 Switch`

---

## 3. Output Channels (Mixer Output Tabs)

Outputs are where your mixes are sent (hardware analog, phones, and digital out).  
**The main output tabs (and output strips) should be:**

| Tab Name               | Output L   | Output R   | Description                      |
|------------------------|------------|------------|----------------------------------|
| Main-Out AN1/AN2       | AN1        | AN2        | Main analog outputs (XLR/Line)   |
| Main-Out PH3/PH4       | PH3        | PH4        | Headphones L/R                   |
| Main-Out AS1/AS2       | AS1        | AS2        | AES or ADAT1/2 (digital)         |
| Main-Out ADAT3/ADAT4   | ADAT3      | ADAT4      | ADAT optical 3/4                 |
| Main-Out ADAT5/ADAT6   | ADAT5      | ADAT6      | ADAT optical 5/6                 |
| Main-Out ADAT7/ADAT8   | ADAT7      | ADAT8      | ADAT optical 7/8                 |

---

## 4. Other Controls (Unpaired or Cross-Patch Inputs)

Some controls exist for advanced patching/mono routing or cross-patching.  
**They are not part of the main stereo pairs above** but can be exposed in advanced/patchbay or mono view.

**Examples:**
- `Mic-AN1-AN2`
- `Line-IN3-AN2`
- `PCM-ADAT5-AN2`
- *(and all other controls ending in `-AN1` or `-AN2` not in the stereo list)*

**These should not appear as default fader strips,  
but may be made available in advanced/mono/patchbay modes.**

---

## 5. Pairing and Grouping Logic

- **Stereo pairs:**  
  For each group, pair channels as (input N, AN1) + (input N+1, AN2).  
  E.g., `Line-ADAT3-AN1` (L) + `Line-ADAT4-AN2` (R)

- **Group order:**  
  MIC → LINE → ADAT (starting with AS1/AS2) → PCM

- **Function controls:**  
  Always displayed with their matching input fader (above or alongside).

- **Outputs:**  
  All output strips (including digital/expansion) appear in the output section.

---

## 6. UI Recommendations

- **Groups separated by labeled headers and spacing.**
- **Stereo pairs displayed as tight, side-by-side fader columns.**
- **Function controls as toggles, switches, or rotary sliders above faders.**
- **ALSA names always visible for clarity and debugging.**
- **Scroll area if all channels do not fit horizontally.**
- **Advanced mode exposes “other”/unpaired controls.**

---

## 7. Why This Layout?

- **Matches the hardware routing logic (as in TotalMix FX and official RME docs)**
- **Reduces confusion by showing only true stereo pairs as strips**
- **Function controls are always available at a glance**
- **Patchbay/advanced users can access every routing possibility if needed**
- **No lost controls or ambiguity**

---

## 8. Summary Table

| Group | Stereo Pair(s) (L/R)                                   | Function Controls                 |
|-------|--------------------------------------------------------|-----------------------------------|
| MIC   | Mic-AN1-AN1 / Mic-AN2-AN2                              | Gain, PAD, 48V                    |
| LINE  | Line-IN3-AN1 / Line-IN4-AN2                            | Gain, Sens.                       |
| ADAT  | Line-AS1-AN1 / Line-AS2-AN2 (ADAT1/2)                  | —                                 |
|       | Line-ADAT3-AN1 / Line-ADAT4-AN2                        | —                                 |
|       | Line-ADAT5-AN1 / Line-ADAT6-AN2                        | —                                 |
|       | Line-ADAT7-AN1 / Line-ADAT8-AN2                        | —                                 |
| PCM   | PCM-AN1-AN1 / PCM-AN2-AN2                              | —                                 |
|       | PCM-PH3-AN1 / PCM-PH4-AN2                              | (System/PCM → Phones → Out)       |
|       | PCM-AS1-AN1 / PCM-AS2-AN2                              | —                                 |
|       | PCM-ADAT3-AN1 / PCM-ADAT4-AN2                          | —                                 |
|       | PCM-ADAT5-AN1 / PCM-ADAT6-AN2                          | —                                 |
|       | PCM-ADAT7-AN1 / PCM-ADAT8-AN2                          | —                                 |

---

**Output Tabs:**

| Tab Name               | Output L   | Output R   | Description                      |
|------------------------|------------|------------|----------------------------------|
| Main-Out AN1/AN2       | AN1        | AN2        | Main analog outputs (XLR/Line)   |
| Main-Out PH3/PH4       | PH3        | PH4        | Headphones L/R                   |
| Main-Out AS1/AS2       | AS1        | AS2        | AES or ADAT1/2 (digital)         |
| Main-Out ADAT3/ADAT4   | ADAT3      | ADAT4      | ADAT optical 3/4                 |
| Main-Out ADAT5/ADAT6   | ADAT5      | ADAT6      | ADAT optical 5/6                 |
| Main-Out ADAT7/ADAT8   | ADAT7      | ADAT8      | ADAT optical 7/8                 |

---

**Other:**  
- IEC958 Emphasis, IEC958 Pro Mask, IEC958 Switch  
- All cross-patch controls not part of main stereo pairs

---

*This layout should be implemented exactly in the mixer UI and patchbay, ensuring all real-world controls are accessible, logically grouped, and clearly labeled for users.*

---

**If anything above needs adjustment, just mark up this doc and we will treat your notes as the new reference.**
