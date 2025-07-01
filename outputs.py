from PyQt6.QtWidgets import QWidget, QTabWidget, QHBoxLayout, QVBoxLayout, QScrollArea
import alsa_backend
from mixer_channels import build_output_map, OUTPUT_TABS
from mixer_widgets import MixerGroupWidget, OutputFaderWidget, StereoPairStrip, ChannelStrip
from alsa_polling import AlsaPollingWorker
from patchbay import PatchbayView

class OutputsTabs(QWidget):
    def __init__(self, card_index=1):
        super().__init__()
        self.tabs = QTabWidget()
        v = QVBoxLayout(self)
        v.addWidget(self.tabs)
        self.setLayout(v)

        # Store ChannelStrips per tab (list of lists)
        self.tab_channel_strips = []

        out_map, func_map = build_output_map(alsa_backend, card_index=1)
        canonical_order = ["Mic", "Line", "ADAT", "PCM"]

        for pair in OUTPUT_TABS:
            tab = QWidget()
            tab_layout = QHBoxLayout(tab)

            # Collect strips for this tab
            tab_strips = []

            # Left: All groups in a scrollable row
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            strip = QWidget()
            h = QHBoxLayout(strip)
            h.setSpacing(50)

            for group in canonical_order:
                group_pairs = out_map[pair].get(group, [])
                if group_pairs:
                    group_widget = MixerGroupWidget(group, group_pairs, func_map)
                    tab_strips += group_widget.findChildren(ChannelStrip)
                    h.addWidget(group_widget)
            h.addStretch()
            strip.setLayout(h)
            scroll.setWidget(strip)
            tab_layout.addWidget(scroll, stretch=10)

            # Right: Output faders (never scrolls)
            out_L, out_R = f"Main-Out {pair[0]}", f"Main-Out {pair[1]}"
            output_widget = OutputFaderWidget(out_L, out_R)
            output_widget.setFixedWidth(260)
            tab_layout.addWidget(output_widget, stretch=0)
            self.tabs.addTab(tab, f"{pair[0]}/{pair[1]}")

            # Add output fader ChannelStrips
            tab_strips += output_widget.findChildren(ChannelStrip)
            # Save for this tab
            self.tab_channel_strips.append(tab_strips)

        # Add Patchbay tab
        patchbay_tab = PatchbayView(card_index=1)
        self.tabs.addTab(patchbay_tab, "Patchbay")
        # Patchbay has no faders for polling
        self.tab_channel_strips.append([])

        # --- Poll only the first tab's channels initially ---
        channel_names = [strip.channel_name for strip in self.tab_channel_strips[0]]
        self.alsa_worker = AlsaPollingWorker(channel_names, interval=0.5)
        self.alsa_worker.alsa_update.connect(self._alsa_update_received)

        # --- Switch polling when tab changes ---
        self.tabs.currentChanged.connect(self._tab_changed)

    def _tab_changed(self, index):
        # Change ALSA poller to only watch the visible tab's strips
        active_strips = self.tab_channel_strips[index]
        if active_strips:  # Skip polling for patchbay tab (empty list)
            channel_names = [strip.channel_name for strip in active_strips]
            self.alsa_worker.set_channels(channel_names)
            self.active_strips = active_strips  # Save for updates
        else:
            # Patchbay tab - stop polling
            self.alsa_worker.set_channels([])
            self.active_strips = []

    def _alsa_update_received(self, values):
        # Only update the visible tab's strips for max efficiency!
        for strip in getattr(self, "active_strips", self.tab_channel_strips[0]):
            val = values.get(strip.channel_name)
            if val is not None and val != strip.fader.slider.value():
                strip.fader.slider.blockSignals(True)
                strip.fader.slider.setValue(val)
                strip.fader.slider.blockSignals(False)
                strip.db_label.setText(f"{val}")

