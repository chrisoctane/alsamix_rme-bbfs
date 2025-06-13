# ALSABAY RME-BBFS Project Primer

**For: RME Babyface Pro FS “TotalMix”–style Routing and Mixer UI (Qt6 + ALSA)** *Last updated: 2025-06-12*

---

## How to Use This Document

* **Paste or upload this markdown to any ChatGPT or Copilot project chat.**
* **Purpose:** Give *full* context, routing logic, naming conventions, UI requirements, and the project’s design goals to any AI or human developer instantly.
* **Tip:** Add new findings/notes to this document over time—future you will thank you!

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Technical Requirements](#technical-requirements)
3. [RME/ALSA Routing Logic (Signal Flow)](#rmealsa-routing-logic-signal-flow)
4. [Channel Name Decoding](#channel-name-decoding)
5. [UI/UX Design Requirements](#uiux-design-requirements)
6. [Auto-Populated Output Tabs: Logic](#auto-populated-output-tabs-logic)
7. [Current Implementation: File Structure](#current-implementation-file-structure)
8. [Magic/Planned Features](#magicplanned-features)
9. [References & Prior Art](#references--prior-art)
10. [How to Onboard a New Contributor/AI](#how-to-onboard-a-new-contributorai)
11. [Appendix: Example ALSA Control List](#appendix-example-alsa-control-list)

---

## 1. Project Overview

**Goal:**
Build a modular, extensible, open-source Qt6+ALSA-based mixer/patchbay GUI for the RME Babyface Pro FS (and similar RME hardware), mimicking and expanding on TotalMix FX routing (minus DSP/FX).

* All ALSA channels/faders visible, draggable, group-move.
* Output tabs for each stereo output pair, auto-populated based on detected routing.
* “Patchbay” style canvas where each ALSA channel (as defined by the driver) can be freely positioned, saved, and used as a routing/mixer reference.
* Per-channel level, pan, stereo link, mute, solo controls.
* Support for complex routing scenarios (mono, stereo, multi-output, submixes).
* Foundation for future RME feature expansion (phantom, pad, metering, etc).

---

## 2. Technical Requirements

* **Platform:** Linux (tested Ubuntu 25.04+, kernel 6.12+)
* **Python:** 3.10+
* **PyQt6:** For modern cross-platform GUI
* **pyalsaaudio:** For full ALSA mixer/control access
* **Modular codebase:** Separation of ALSA backend, patchbay logic, and GUI main window.
* **Extensible:** Should support future RME devices (naming scheme, routing logic).
* **ALSA driver knowledge:** Code must parse/control all Babyface Pro FS mixer elements, including Main-Out, PCM, Mic, Line, ADAT, AS, PH, etc.

---

## 3. RME/ALSA Routing Logic (Signal Flow)

### Routing Principles

* **Each ALSA “mixer” control is an audio path:**
  Format: `<typ>-<src>-<dst>`

  * `<typ>` = signal “source” (e.g., PCM, Mic, Line, AS, PH)
  * `<src>` = input channel or logical “bus” (e.g., AN1, AN2, ADAT3, AS1, PH3, etc)
  * `<dst>` = physical output channel (“Main-Out”, “ADAT”, “PH”, etc)

#### Examples

* **PCM-AN1-AN1** → Main\_Out AN1 (system audio L channel routed to main output L)
* **PCM-AN2-AN2** → Main\_Out AN2 (system audio R channel to main output R)
* **PCM-AN2-AN1** → Main\_Out AN1 (system R channel routed to left output — mono pan/dual output)
* **AS1-PH3-ADAT7** → Main\_Out ADAT7 (mix of input and headphone routed to ADAT output)
* **Main-Out AN1** (master physical output fader for AN1)
* **Mic-AN1-AN2** (Mic channel 1 routed to output 2)

#### Fader Control Logic

* **Each source-destination pair has its own level fader.**
* **Main-Out faders** control final output gain after all mix busses summed.
* **Pan/mute/solo logic** follows the same routing:

  * *Pan* is implemented by adjusting the mix of `<src>` across paired `<dst>` channels.
  * *Stereo link* moves both faders/pans together.
  * *Mute/solo* control the channel-to-output bus.

---

## 4. Channel Name Decoding

### ALSA Mixer Naming (Babyface Pro FS Example)

* `PCM-AN1-AN1` = (PCM, Analog In 1, Analog Out 1)
* `PCM-AS1-PH3` = (PCM, ADAT/Software Input 1, Phones 3)
* `Mic-AN1-AN2` = (Mic Input 1, Analog Out 2)
* `Main-Out AN1` = Physical output fader for Analog Out 1
* etc.

**Regex Example for Extraction:**
`r"(PCM|Line|Mic|Main-Out|IEC958|AS|PH)[-_]([A-Z0-9]+)[-_]([A-Z0-9]+)"`

---

## 5. UI/UX Design Requirements

* **Patchbay Canvas**

  * One draggable “fader box” per ALSA control, all rendered to scale.
  * Drag handle at left; label shows ALSA name (auto-sized).
  * Group selection and group drag.
  * Black/yellow header for all “Main-Out” channels.
  * Scene auto-expands as channels are dragged to the edges.
  * Save/load JSON layout.

* **Output Tabs**

  * Each main output pair gets a tab (AN1/AN2, PH3/PH4, ADAT3/4, etc).
  * Tab auto-populates with all “inputs” (controls) routed to that output.
  * Each input in tab gets:

    * Fader (level)
    * Pan slider/knob
    * Stereo link
    * Mute, solo
    * Label showing driver/decoded name

* **Main Controls**

  * Toolbar: Save/load/reset (“reset” = relayout, not reload)
  * Zoom slider for patchbay
  * Window title, clear branding/version

---

## 6. Auto-Populated Output Tabs: Logic

* For each “main out” (AN1/AN2, PH3/PH4, etc), find all controls with `<dst>` matching that output.
* Populate the tab with a fader per input/control, grouped by source (PCM, Mic, Line, AS, etc).
* For mono sources routed to stereo outputs, pan logic is “per ALSA control” (e.g., PCM-AN1-AN2 + PCM-AN2-AN2 control L/R level).
* Stereo link buttons synchronize fader/pan for a pair.
* The physical output master (“Main-Out ANx”) is always present at right of tab.

---

## 7. Current Implementation: File Structure

```
alsabay_rme-bbfs/
│
├── alsa_backend.py   # ALSA interface, channel name parsing, volume helpers
├── patchbay.py       # Patchbay UI, draggable faders, group select/drag, layout save/load
├── outputs.py        # Output tab UI: auto-population, routing logic, per-tab controls
└── main.py           # App startup and glue (window, menus, toolbar)
```

---

## 8. “Magic”/Planned Features

* Auto-populate output tabs based on routing (DONE).
* Group drag by handle (DONE), group selection (DONE).
* Patchbay with persistent, resizable, zoomable scene (DONE).
* Pan law compensation, trim/pad, -10/+4 switches.
* Mono/stereo switch, mono pan law logic.
* Hide/show (soft-mute) channels.
* Global mute/solo/undo.
* Detect all connected RME devices, allow device selection (multi-device support).
* Settings dialog for colors, themes, etc.
* *Future*: Patch connections via drag wires (like QjackCtl graph).
* *Future*: Automatic detection of new controls for firmware upgrades, hotplug, etc.

---

## 9. References & Prior Art

* [RME TotalMix FX](https://www.rme-audio.de/totalmix-fx.html)
* [QjackCtl](https://qjackctl.sourceforge.io/)
* [AlsaMixer GUI](https://github.com/alsa-project/alsamixer)
* [RME Linux class-compliant info](https://www.forum.rme-audio.de/viewtopic.php?id=34386)
* [Babyface Pro FS ALSA Driver Controls](https://github.com/alsa-project/alsa-ucm-conf/blob/master/ucm2/USB-Audio/USB-Audio.conf)

---

## 10. How to Onboard a New Contributor/AI

* Upload/copy this primer.
* Upload the latest project files.
* Give a quick summary of your goal for the current coding session (e.g., “Fix pan law for mono/stereo routing”).
* If you have specific test signals/scenarios, document those here!

---

## 11. Appendix: Example ALSA Control List

**(Short sample for reference — see your own **\`\`** for full list)**

```
PCM-AN1-AN1
PCM-AN2-AN2
PCM-AN2-AN1
PCM-AS1-AN1
Mic-AN1-AN1
Line-ADAT3-AN1
Main-Out AN1
Main-Out AN2
Main-Out PH3
Main-Out PH4
# ...etc
```

---

*Maintained by: chris\@ed-5950x, project lead.*
